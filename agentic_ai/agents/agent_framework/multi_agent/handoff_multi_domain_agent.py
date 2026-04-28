"""Multi-domain handoff agent built on the native ``HandoffBuilder``.

This module migrates the previous hand-rolled handoff implementation
(intent classification + regex-based handoff detection + manual context
transfer) to the native handoff orchestration introduced in
``agent-framework`` 1.2.x.

Architecture:

1. Each domain specialist is a regular ``Agent`` configured with a
   filtered MCP tool set.
2. ``HandoffBuilder`` constructs a workflow where every agent can hand off
   to every other agent (mesh topology). The framework auto-injects
   synthetic ``handoff_to_<target>`` tools into each agent and intercepts
   them via middleware to route control — no more manual handoff
   detection.
3. Cross-request continuity is handled via the workflow's checkpointing
   (``with_checkpointing``). The first turn starts a fresh run; subsequent
   turns resume by responding to the pending ``request_info`` event with
   the new user prompt.
4. Streaming agent updates and ``handoff_sent`` events are forwarded to
   the WebSocket layer to preserve the existing UI behaviour
   (``agent_start``, ``agent_token``, ``tool_called``,
   ``handoff_announcement``, ``final_result``).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from agent_framework import (
    Agent as FrameworkAgent,
    ChatOptions,
    MCPStreamableHTTPTool,
)
from agent_framework.openai import OpenAIChatClient
from agent_framework_orchestrations import (
    HandoffAgentUserRequest,
    HandoffBuilder,
    HandoffSentEvent,
)

from agents.base_agent import BaseAgent, ToolCallTrackingMixin
from agents.agent_framework.utils import create_filtered_tool_list
from agents.agent_framework.multi_agent.checkpoint_storage import (
    create_checkpoint_storage,
    prune_checkpoints,
)

logger = logging.getLogger(__name__)


# Domain definitions for the handoff workflow.
#
# ``description`` is consumed by ``HandoffBuilder`` to populate the
# auto-generated handoff tool description, so it must clearly state when
# control should transfer to that specialist.
DOMAINS: Dict[str, Dict[str, Any]] = {
    "crm_billing": {
        "name": "CRM & Billing Specialist",
        "description": (
            "Handles customer accounts, subscriptions, billing, invoices, "
            "payments, data usage and account adjustments."
        ),
        "tools": [
            "get_all_customers",
            "get_customer_detail",
            "get_subscription_detail",
            "get_billing_summary",
            "get_invoice_payments",
            "pay_invoice",
            "get_data_usage",
            "update_subscription",
            "search_knowledge_base",
        ],
        "instructions": (
            "You are the CRM & Billing Specialist for Contoso support.\n\n"
            "**Your expertise:**\n"
            "- Customer accounts, subscriptions, billing, invoices, payments\n"
            "- Account adjustments, data usage, subscription updates\n\n"
            "**Critical rules:**\n"
            "- ALWAYS use your tools to retrieve factual data. NEVER guess or hallucinate.\n"
            "- If customer info is needed but not provided, ask the user directly for it.\n"
            "- If the user asks about products, promotions, or security/authentication issues, "
            "you MUST hand off to the appropriate specialist by calling the corresponding "
            "handoff tool. Do not attempt to answer outside your domain.\n"
            "- Be concise and professional. Provide specific details from tool responses.\n"
        ),
    },
    "product_promotions": {
        "name": "Product & Promotions Specialist",
        "description": (
            "Handles product catalog inquiries, plan changes, promotions, "
            "eligibility checks and customer orders."
        ),
        "tools": [
            "get_products",
            "get_product_detail",
            "get_promotions",
            "get_eligible_promotions",
            "get_customer_orders",
            "search_knowledge_base",
        ],
        "instructions": (
            "You are the Product & Promotions Specialist for Contoso support.\n\n"
            "**Your expertise:**\n"
            "- Product catalog, features, availability\n"
            "- Promotions, discounts, eligibility rules\n"
            "- Customer orders and product recommendations\n\n"
            "**Critical rules:**\n"
            "- ALWAYS use your tools to retrieve factual data. NEVER guess or hallucinate.\n"
            "- If the user asks about billing or security/authentication issues, you MUST "
            "hand off to the appropriate specialist by calling the corresponding handoff "
            "tool. Do not attempt to answer outside your domain.\n"
            "- Be enthusiastic and helpful. Highlight benefits and savings opportunities.\n"
        ),
    },
    "security_authentication": {
        "name": "Security & Authentication Specialist",
        "description": (
            "Handles authentication failures, account lockouts, security "
            "incidents and remediation."
        ),
        "tools": [
            "get_security_logs",
            "unlock_account",
            "get_support_tickets",
            "create_support_ticket",
            "search_knowledge_base",
        ],
        "instructions": (
            "You are the Security & Authentication Specialist for Contoso support.\n\n"
            "**Your expertise:**\n"
            "- Account security, authentication issues, lockouts\n"
            "- Security logs, incident investigation, remediation\n"
            "- Support ticket management for security issues\n\n"
            "**Critical rules:**\n"
            "- ALWAYS use your tools to retrieve factual data. NEVER guess or hallucinate.\n"
            "- If the user asks about billing or products/promotions, you MUST hand off "
            "to the appropriate specialist by calling the corresponding handoff tool. "
            "Do not attempt to answer outside your domain.\n"
            "- Take security seriously. Verify user identity and flag suspicious activity.\n"
        ),
    },
}


class _CheckpointRetention:
    """How many checkpoints per workflow to keep on disk/in-memory."""

    DEFAULT = 5


class Agent(ToolCallTrackingMixin, BaseAgent):
    """Multi-domain handoff agent backed by the native ``HandoffBuilder``."""

    def __init__(
        self,
        state_store: Dict[str, Any],
        session_id: str,
        access_token: str | None = None,
    ) -> None:
        super().__init__(state_store, session_id)
        self._access_token = access_token
        self._ws_manager = None

        self._workflow: Any = None
        self._initialized = False
        self._domain_agents: Dict[str, FrameworkAgent] = {}
        self._mcp_tool: Optional[MCPStreamableHTTPTool] = None

        # Checkpoint storage uses the built-in 1.2.1 backends (in-memory by
        # default; FileCheckpointStorage / CosmosCheckpointStorage when
        # WORKFLOW_CHECKPOINT_BACKEND is set). The helper caches one storage
        # instance per session inside the process so successive HTTP requests
        # share state.
        self._workflow_name = f"handoff-{session_id}"
        self._checkpoint_storage = create_checkpoint_storage(session_id)

        # Track the pending ``request_info`` ID so the next turn can resume.
        self._pending_request_id_key = f"{session_id}_handoff_pending_req"
        self._pending_request_id: Optional[str] = state_store.get(self._pending_request_id_key)

        # Current speaking domain (used for UI hints + start-agent selection
        # on resume after a process restart).
        self._current_domain_key = f"{session_id}_current_domain"
        self._current_domain: Optional[str] = state_store.get(self._current_domain_key)

        # Turn tracking for tool grouping
        self._turn_key = f"{session_id}_handoff_turn"
        self._current_turn = state_store.get(self._turn_key, 0)

        self.init_tool_tracking()

        self._default_domain = os.getenv("HANDOFF_DEFAULT_DOMAIN", "crm_billing")
        if self._default_domain not in DOMAINS:
            logger.warning(
                "[HANDOFF] HANDOFF_DEFAULT_DOMAIN=%s is not a known domain; falling back to crm_billing",
                self._default_domain,
            )
            self._default_domain = "crm_billing"

        logger.info(
            "[HANDOFF] Configuration: default_domain=%s current_domain=%s pending_req=%s",
            self._default_domain,
            self._current_domain,
            self._pending_request_id,
        )

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject a WebSocket manager for streaming events."""
        self._ws_manager = manager
        logger.info("[HANDOFF] WebSocket manager set, session_id=%s", self.session_id)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    async def _setup(self) -> None:
        if self._initialized:
            return

        has_api_key = bool(self.azure_openai_key)
        has_credential = bool(self.azure_credential)

        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure "
                "AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set."
            )
        if not has_api_key and not has_credential:
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Either set AZURE_OPENAI_API_KEY "
                "or ensure managed identity is available for credential-based authentication."
            )

        headers = self._build_headers()
        self._mcp_tool = await self._create_mcp_tool(headers)
        if self._mcp_tool is not None:
            await self._mcp_tool.__aenter__()
            logger.info(
                "[HANDOFF] Connected to MCP server, loaded %d tools",
                len(self._mcp_tool.functions),
            )

        if has_api_key:
            chat_client = OpenAIChatClient(
                api_key=self.azure_openai_key,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
            logger.info("[HANDOFF] Using API key authentication for Azure OpenAI")
        else:
            chat_client = OpenAIChatClient(
                credential=self.azure_credential,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
            logger.info("[HANDOFF] Using managed identity authentication for Azure OpenAI")

        # Build one Agent per domain. ``require_per_service_call_history_persistence``
        # is required by HandoffBuilder because the framework injects middleware
        # that short-circuits handoff tool calls (MiddlewareTermination); without
        # this flag local history providers would persist tool results the
        # service never observed.
        for domain_id, cfg in DOMAINS.items():
            domain_tools = create_filtered_tool_list(
                base_mcp_tool=self._mcp_tool,
                allowed_tool_names=cfg["tools"],
                agent_name=domain_id,
            )
            agent = FrameworkAgent(
                client=chat_client,
                name=domain_id,
                description=cfg["description"],
                instructions=cfg["instructions"],
                tools=domain_tools,
                default_options=ChatOptions(model=self.azure_deployment),
                require_per_service_call_history_persistence=True,
            )
            await agent.__aenter__()
            self._domain_agents[domain_id] = agent

        # Choose start agent: prefer the domain that handled the prior turn
        # (so a fresh process can route the next message to the same specialist),
        # otherwise fall back to the configured default. Note: ``with_start_agent``
        # only matters when there is no checkpoint to resume from.
        start_id = (
            self._current_domain
            if self._current_domain in self._domain_agents
            else self._default_domain
        )

        # Default mesh topology (no add_handoff calls = every agent can hand
        # off to every other agent), which matches the previous "any specialist
        # can route anywhere" behaviour.
        self._workflow = (
            HandoffBuilder(
                name=self._workflow_name,
                participants=list(self._domain_agents.values()),
            )
            .with_start_agent(self._domain_agents[start_id])
            .with_checkpointing(self._checkpoint_storage)
            .build()
        )

        self._initialized = True
        logger.info(
            "[HANDOFF] Initialized %d domain specialists with native HandoffBuilder; start=%s",
            len(self._domain_agents),
            start_id,
        )

    def _build_headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    async def _create_mcp_tool(self, headers: Dict[str, str]) -> MCPStreamableHTTPTool | None:
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI is not configured; agents will run without MCP tools.")
            return None
        return MCPStreamableHTTPTool(
            name="mcp-streamable",
            url=self.mcp_server_uri,
            headers=headers,
            timeout=30,
            request_timeout=30,
        )

    # ------------------------------------------------------------------
    # Chat entry point
    # ------------------------------------------------------------------
    async def chat_async(self, prompt: str) -> str:
        await self._setup()
        self.clear_tool_calls()

        self._current_turn += 1
        self.state_store[self._turn_key] = self._current_turn

        # Look up the most recent checkpoint via the public 1.2.x
        # CheckpointStorage protocol so any backend (memory / file / cosmos)
        # works without bespoke plumbing.
        latest_checkpoint_obj = await self._checkpoint_storage.get_latest(
            workflow_name=self._workflow_name
        )
        latest_checkpoint = latest_checkpoint_obj.checkpoint_id if latest_checkpoint_obj else None

        # Resume an in-flight workflow (typical path after the first turn) by
        # responding to the pending HandoffAgentUserRequest with the new user
        # message. Otherwise start a fresh run.
        if latest_checkpoint and self._pending_request_id:
            user_msgs = HandoffAgentUserRequest.create_response(prompt)
            stream = self._workflow.run(
                responses={self._pending_request_id: user_msgs},
                checkpoint_id=latest_checkpoint,
                stream=True,
            )
            logger.info(
                "[HANDOFF] Resuming workflow from checkpoint=%s with pending request=%s",
                latest_checkpoint,
                self._pending_request_id,
            )
        else:
            stream = self._workflow.run(prompt, stream=True)
            logger.info("[HANDOFF] Starting fresh handoff workflow run")

        active_agent_id: Optional[str] = self._current_domain or self._default_domain
        per_agent_text: Dict[str, List[str]] = {}
        new_pending_request_id: Optional[str] = None

        # Announce the initial speaking agent so the UI shows activity even
        # before the first token arrives.
        await self._notify_agent_start(active_agent_id, is_handoff=False)

        try:
            async for event in stream:
                etype = event.type

                if etype == "handoff_sent":
                    data = event.data  # HandoffSentEvent
                    src_id = getattr(data, "source", None) or active_agent_id or ""
                    tgt_id = getattr(data, "target", None) or ""
                    logger.info("[HANDOFF] handoff_sent: %s -> %s", src_id, tgt_id)
                    await self._notify_handoff(src_id, tgt_id)
                    if tgt_id:
                        active_agent_id = tgt_id
                        await self._notify_agent_start(tgt_id, is_handoff=True)
                    continue

                if etype == "output" and event.executor_id in self._domain_agents:
                    update = event.data  # AgentResponseUpdate
                    if update is None:
                        continue
                    await self._handle_agent_update(event.executor_id, update, per_agent_text)
                    continue

                if etype == "request_info":
                    new_pending_request_id = event.request_id
                    continue
        except Exception as exc:
            logger.error("[HANDOFF] Workflow error: %s", exc, exc_info=True)
            raise

        # Finalize any in-flight tool tracking
        self.finalize_tool_tracking()

        # Pick the response that should be returned to the user — the last
        # agent to speak (which is ``active_agent_id`` after any handoffs).
        if active_agent_id and active_agent_id in per_agent_text:
            assistant_response = "".join(per_agent_text[active_agent_id])
        else:
            # Fallback: concatenate all speaker output in order
            assistant_response = "".join(t for buf in per_agent_text.values() for t in buf)

        # Persist resumption state for the next turn
        self._pending_request_id = new_pending_request_id
        if new_pending_request_id is not None:
            self.state_store[self._pending_request_id_key] = new_pending_request_id
        else:
            self.state_store.pop(self._pending_request_id_key, None)

        if active_agent_id:
            self._current_domain = active_agent_id
            self.state_store[self._current_domain_key] = active_agent_id

        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {"type": "final_result", "content": assistant_response},
            )

        # Mirror the conversation in the BaseAgent chat history (used by the
        # backend's history APIs and the magentic_group context-transfer logic).
        self.append_to_chat_history(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_response},
            ]
        )
        self._setstate({"mode": "handoff_multi_domain", "current_domain": self._current_domain})

        # Cap retained checkpoints to avoid unbounded growth across long
        # conversations; mirrors the previous _RETENTION=5 behaviour but uses
        # the public CheckpointStorage protocol so any backend benefits.
        await prune_checkpoints(
            self._checkpoint_storage,
            self._workflow_name,
            retain=_CheckpointRetention.DEFAULT,
        )

        return assistant_response

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------
    async def _handle_agent_update(
        self,
        executor_id: str,
        update: Any,
        per_agent_text: Dict[str, List[str]],
    ) -> None:
        contents = getattr(update, "contents", None) or []
        for content in contents:
            ctype = getattr(content, "type", None)
            if ctype == "function_call":
                name = getattr(content, "name", None)
                if name and not name.startswith("handoff_to_"):
                    # Real domain tool — track for the UI. Synthetic handoff
                    # tools are filtered out because the framework already
                    # surfaces those as ``handoff_sent`` events.
                    self.track_function_call_start(name)
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "tool_called",
                                "agent_id": executor_id,
                                "tool_name": name,
                                "turn": self._current_turn,
                            },
                        )
                args_chunk = getattr(content, "arguments", "")
                if args_chunk:
                    self.track_function_call_arguments(args_chunk)
            elif ctype == "function_result":
                self.finalize_tool_tracking()

        text = getattr(update, "text", None)
        if text:
            per_agent_text.setdefault(executor_id, []).append(text)
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "agent_token",
                        "agent_id": executor_id,
                        "content": text,
                    },
                )

    async def _notify_agent_start(self, agent_id: Optional[str], *, is_handoff: bool) -> None:
        if not self._ws_manager or not agent_id:
            return
        cfg = DOMAINS.get(agent_id, {})
        await self._ws_manager.broadcast(
            self.session_id,
            {
                "type": "agent_start",
                "agent_id": agent_id,
                "agent_name": cfg.get("name", agent_id),
                # Handoffs should appear in the UI's left "internal process" panel;
                # the very first agent_start of a turn should not.
                "show_message_in_internal_process": is_handoff,
            },
        )

    async def _notify_handoff(self, from_id: str, to_id: str) -> None:
        if not self._ws_manager:
            return
        to_name = DOMAINS.get(to_id, {}).get("name", to_id)
        msg = f"I'll connect you with our {to_name} who can better assist with that."
        await self._ws_manager.broadcast(
            self.session_id,
            {
                "type": "handoff_announcement",
                "from_domain": from_id,
                "to_domain": to_id,
                "message": msg,
            },
        )
