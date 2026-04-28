import asyncio
import inspect
import json
import logging
import os
from typing import Any, Callable, Dict, Iterable, List, Optional, cast

from agent_framework import (
    Agent as FrameworkAgent,
    ChatOptions,
    MCPStreamableHTTPTool,
    WorkflowEvent,
    CheckpointStorage,
    ResponseStream,
    WorkflowRunResult,
)
from agent_framework_orchestrations import (
    MagenticBuilder,
    MagenticOrchestratorEvent,
    MagenticOrchestratorEventType,
    MagenticPlanReviewRequest,
    MagenticPlanReviewResponse,
)
from agent_framework.openai import OpenAIChatClient

from agents.base_agent import BaseAgent, ToolCallTrackingMixin
from agents.agent_framework.utils import create_filtered_tool_list
from agents.agent_framework.multi_agent.checkpoint_storage import (
    _coerce_checkpoint_storage,
    create_checkpoint_storage,
    prune_checkpoints,
    purge_checkpoints,
)

logger = logging.getLogger(__name__)


_CHECKPOINT_RETENTION = 5


class Agent(ToolCallTrackingMixin, BaseAgent):
    """Agent Framework implementation of the collaborative Magentic team."""

    DEFAULT_MANAGER_INSTRUCTIONS = (
        "You are the Analysis & Planning orchestrator for a team of internal specialists handling Contoso customer support. "
        "**CRITICAL: You are the ONLY agent that communicates directly with the customer. Specialists communicate only with YOU.** "
        "Break down the user's needs, decide which specialist should respond, and integrate their findings into the final customer-facing answer. "
        "**IMPORTANT: Instruct participants to use their tools to retrieve factual data. Do not allow speculative or hallucinated answers.** "
        "Each participant MUST call the appropriate tool and cite the tool results (with IDs, timestamps, or specific data points) in their response to you. "
        "**If a specialist reports they need more information from the user (like customer ID, account details, etc.), "
        "YOU must translate that into a polite customer-facing request and deliver it as FINAL_ANSWER immediately - do NOT loop or wait.** "
        "After gathering sufficient information from specialists (typically 1-3 rounds), synthesize their responses into "
        "a clear, customer-friendly answer and deliver it prefixed with 'FINAL_ANSWER:'. "
        "**DO NOT loop indefinitely - once you have tool-backed answers OR a request for user information, conclude with FINAL_ANSWER.**"
    )

    CUSTOM_PROGRESS_LEDGER_PROMPT = """
Recall we are working on the following request:

{task}

And we have assembled the following team:

{team}

To make progress on the request, please answer the following questions, including necessary reasoning:

    - Is the request fully satisfied? (True if EITHER:
      a) The original request has been SUCCESSFULLY and FULLY addressed with factual, tool-backed answers, OR
      b) We need additional information or clarification from the user that we cannot obtain ourselves
      (e.g., customer ID, account number, email, phone, personal preferences, missing context that only the user can provide).
      
      False if the original request has NOT been addressed AND we have all the information we need to continue working.)
      
    - Are we in a loop where we are repeating the same requests and or getting the same responses as before?
      Loops can span multiple turns, and can include repeated actions. NOTE: If specialists say they "need customer ID"
      or similar user information, that is NOT a loop - it means we should complete with a request to the user
      (is_request_satisfied=True).
      
    - Are we making forward progress? (True if just starting, or recent messages are adding value or identifying needed
      information. False if recent messages show evidence of being stuck in a loop or if there is evidence of significant
      barriers to success. NOTE: Specialists identifying that they need user information IS forward progress - they've
      determined what's needed to proceed.)
      
    - Who should speak next? (select from: {names}. NOTE: If is_request_satisfied is True because we need user
      input, this field is ignored but you must still provide a valid name from the list.)
      
    - What instruction or question would you give this team member? (If is_request_satisfied is True because we
      need user input, phrase this as a polite, customer-facing question asking for the missing information.
      Otherwise, phrase as if speaking directly to the specialist team member, and include any specific information
      they may need to complete their task.)

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is.
DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

{{
    "is_request_satisfied": {{
        "reason": string (explain whether we have a complete answer OR need user input to proceed),
        "answer": boolean
    }},
    "is_in_loop": {{
        "reason": string,
        "answer": boolean
    }},
    "is_progress_being_made": {{
        "reason": string,
        "answer": boolean
    }},
    "next_speaker": {{
        "reason": string,
        "answer": string (select from: {names})
    }},
    "instruction_or_question": {{
        "reason": string,
        "answer": string (if is_request_satisfied=True and we need user input, phrase this as a polite user-facing question)
    }}
}}
"""

    def __init__(
        self,
        state_store: Dict[str, Any],
        session_id: str,
        access_token: str | None = None,
        *,
        config: Optional[Dict[str, Any]] = None,
        checkpoint_storage_factory: Optional[
            Callable[[Dict[str, Any], str], CheckpointStorage]
        ] = None,
    ) -> None:
        super().__init__(state_store, session_id)
        self._access_token = access_token
        self._config = self._load_effective_config(config)
        self._checkpoint_storage_factory = (
            checkpoint_storage_factory
            or self.state_store.get("magentic_checkpoint_storage_factory")
        )
        storage_override = self.state_store.get("magentic_checkpoint_storage")
        self._checkpoint_storage_override: Optional[CheckpointStorage] = _coerce_checkpoint_storage(
            storage_override
        )
        if storage_override and not self._checkpoint_storage_override:
            logger.warning(
                "[AgentFramework-Magentic] Ignoring checkpoint storage override because it does not implement CheckpointStorage."
            )
        self._participant_client: Optional[OpenAIChatClient] = None
        self._manager_client: Optional[OpenAIChatClient] = None
        self._workflow_event_logging_enabled = bool(self._config.get("log_workflow_events", False))
        self._enable_plan_review = bool(self._config.get("enable_plan_review", False))
        self._manager_instructions = self._config.get(
            "manager_instructions", self.DEFAULT_MANAGER_INSTRUCTIONS
        )
        self._max_round_count = int(self._config.get("max_round_count", 4))
        self._max_stall_count = int(self._config.get("max_stall_count", 2))
        self._max_reset_count = int(self._config.get("max_reset_count", 1))
        self._participant_overrides: Dict[str, Dict[str, Any]] = self._config.get("participant_overrides", {})
        self._pending_prompt_state_key = f"{self.session_id}_magentic_pending_prompt"
        # The workflow name is captured after the first build() and reused so
        # successive HTTP requests can locate prior checkpoints via the
        # standardized CheckpointStorage protocol (get_latest(workflow_name=...)).
        self._workflow_name_state_key = f"{self.session_id}_magentic_workflow_name"
        self._ws_manager = None  # Will be set from backend if available
        self._stream_agent_id: Optional[str] = None
        self._stream_line_open: bool = False
        self._last_agent_message: Optional[str] = None  # Track last agent message for deduplication

        # Initialize tool tracking from mixin
        self.init_tool_tracking()

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager

    async def chat_async(self, prompt: str) -> str:
        self._validate_configuration()

        checkpoint_storage = self._create_checkpoint_storage()

        headers = self._build_headers()
        tools = await self._maybe_create_tools(headers)

        # First resume any previous unfinished run before processing the new prompt
        resume_answer = await self._resume_previous_run(checkpoint_storage, tools)
        if resume_answer:
            logger.info("[AgentFramework-Magentic] Resumed unfinished workflow before handling new prompt.")

        participant_client = self._get_participant_client()
        manager_client = self._get_manager_client()

        task = self._render_task_with_history(prompt)
        self._mark_pending_prompt(prompt)

        workflow = await self._build_workflow(participant_client, manager_client, tools, checkpoint_storage)

        final_answer = await self._run_workflow(workflow, checkpoint_storage, task)
        if final_answer is None:
            logger.warning(
                "[AgentFramework-Magentic] No final answer produced; leaving checkpoint for potential resume."
            )
            return (
                "The agent team is still working through the previous request. Please try again in a moment so we "
                "can resume from the saved progress."
            )

        cleaned_answer = self._sanitize_final_answer(final_answer)
        if cleaned_answer is None:
            return (
                "The Magentic coordinator could not produce a final response. Please try again later or contact support."
            )

        self.append_to_chat_history(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": cleaned_answer},
            ]
        )

        await self._reset_checkpoint_progress(checkpoint_storage)
        self._setstate({"mode": "magentic_collaboration"})

        return cleaned_answer

    def _validate_configuration(self) -> None:
        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure AZURE_OPENAI_CHAT_DEPLOYMENT, "
                "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set."
            )
        # Either an API key or a managed-identity credential must be available.
        # _build_chat_client falls back to azure_credential when azure_openai_key
        # is unset; the other agents in this package follow the same pattern.
        if not self.azure_openai_key and not getattr(self, "azure_credential", None):
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Set AZURE_OPENAI_API_KEY "
                "or provide a managed-identity credential."
            )

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _maybe_create_tools(self, headers: Dict[str, str]) -> List[MCPStreamableHTTPTool] | None:
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI is not configured; multi-agent team will run without MCP tools.")
            return None

        logger.info(f"[MCP SETUP] Creating MCP tool with URI: {self.mcp_server_uri}")
        request_headers = dict(headers)
        header_overrides = self._config.get("mcp_headers")
        if isinstance(header_overrides, dict):
            request_headers.update({str(key): str(value) for key, value in header_overrides.items()})

        logger.info(f"[MCP SETUP] Request headers: {list(request_headers.keys())}")
        timeout_seconds = int(self._config.get("mcp_timeout_seconds", 30))
        request_timeout_seconds = int(self._config.get("mcp_request_timeout_seconds", timeout_seconds))
        retry_attempts = max(1, int(self._config.get("mcp_startup_retries", 1)))
        retry_backoff = float(self._config.get("mcp_retry_backoff_seconds", 2.0))

        last_error: Exception | None = None
        for attempt in range(1, retry_attempts + 1):
            try:
                tool = MCPStreamableHTTPTool(
                    name="mcp-streamable",
                    url=self.mcp_server_uri,
                    headers=request_headers,
                    timeout=timeout_seconds,
                    request_timeout=request_timeout_seconds,
                )
                logger.info(f"[MCP SETUP] Successfully created MCP tool: {tool}")
                return [tool]
            except Exception as exc:  # pragma: no cover - defensive path
                last_error = exc
                if attempt < retry_attempts:
                    wait_time = retry_backoff * attempt
                    logger.warning(
                        "Failed to initialise MCP tool (attempt %s/%s): %s. Retrying in %.1fs.",
                        attempt,
                        retry_attempts,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Failed to initialise MCP tool after %s attempts: %s",
                        retry_attempts,
                        exc,
                        exc_info=True,
                    )

        return None

    def _get_participant_client(self) -> OpenAIChatClient:
        if self._participant_client is None:
            self._participant_client = self._build_chat_client()
        return self._participant_client

    def _get_manager_client(self) -> OpenAIChatClient:
        if self._manager_client is None:
            self._manager_client = self._build_chat_client()
        return self._manager_client

    def _build_chat_client(self) -> OpenAIChatClient:
        # Use API key if available, otherwise use credential-based authentication
        if self.azure_openai_key:
            logger.info("[AgentFramework-Magentic] Using API key authentication for Azure OpenAI")
            return OpenAIChatClient(
                api_key=self.azure_openai_key,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
        elif self.azure_credential:
            logger.info("[AgentFramework-Magentic] Using managed identity authentication for Azure OpenAI")
            return OpenAIChatClient(
                credential=self.azure_credential,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
        else:
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Either set AZURE_OPENAI_API_KEY "
                "or ensure managed identity is available for credential-based authentication."
            )

    async def _resume_previous_run(
        self,
        checkpoint_storage: CheckpointStorage,
        tools: List[MCPStreamableHTTPTool] | None,
    ) -> str | None:
        resume_id = await self._get_latest_checkpoint_id(checkpoint_storage)
        if not resume_id:
            return None

        logger.info("[AgentFramework-Magentic] Attempting to resume workflow from checkpoint %s", resume_id)
        participant_client = self._get_participant_client()
        manager_client = self._get_manager_client()
        workflow = await self._build_workflow(participant_client, manager_client, tools, checkpoint_storage)

        try:
            final_answer = await self._run_workflow(workflow, checkpoint_storage, None, resume_id)
        except Exception as exc:  # pragma: no cover - defensive resume path
            logger.error("[AgentFramework-Magentic] Failed to resume workflow: %s", exc, exc_info=True)
            await self._reset_checkpoint_progress(checkpoint_storage)
            return None

        if final_answer is None:
            await self._reset_checkpoint_progress(checkpoint_storage)
            return None

        cleaned_answer = self._sanitize_final_answer(final_answer)
        if cleaned_answer is None:
            await self._reset_checkpoint_progress(checkpoint_storage)
            return None
        original_prompt = self._consume_pending_prompt()
        if original_prompt:
            self.append_to_chat_history(
                [
                    {"role": "user", "content": original_prompt},
                    {"role": "assistant", "content": cleaned_answer},
                ]
            )
        else:
            self.append_to_chat_history(
                [
                    {"role": "assistant", "content": cleaned_answer},
                ]
            )

        await self._reset_checkpoint_progress(checkpoint_storage)
        return cleaned_answer

    async def _build_workflow(
        self,
        participant_client: OpenAIChatClient,
        manager_client: OpenAIChatClient,
        tools: List[MCPStreamableHTTPTool] | None,
        checkpoint_storage: CheckpointStorage,
    ) -> Any:
        participants = await self._create_participants(participant_client, tools)

        # Note: Streaming is now handled in _run_workflow by processing events from run()
        if self._ws_manager:
            logger.info(f"[STREAMING] WebSocket manager available for session_id={self.session_id}")
            logger.info("[STREAMING] Events will be streamed via run(stream=True) processing")
        
        # Create manager agent for the StandardMagenticManager
        manager_agent = FrameworkAgent(
            client=manager_client,
            name="magentic_manager",
            instructions=self._manager_instructions,
        )
        
        # Build the MagenticBuilder with constructor kwargs (RC1 API)
        builder = MagenticBuilder(
            participants=list(participants.values()),
            manager_agent=manager_agent,
            max_round_count=self._max_round_count,
            max_stall_count=self._max_stall_count,
            max_reset_count=self._max_reset_count,
            progress_ledger_prompt=self.CUSTOM_PROGRESS_LEDGER_PROMPT,
            checkpoint_storage=checkpoint_storage,
            enable_plan_review=self._enable_plan_review,
        )

        workflow = builder.build()
        # MagenticBuilder generates a random workflow name (e.g.
        # ``WorkflowBuilder-<uuid>``) per build. Persist it in the per-session
        # state_store so subsequent requests can call
        # ``storage.get_latest(workflow_name=...)`` to find prior checkpoints.
        self.state_store[self._workflow_name_state_key] = workflow.name
        return workflow

    async def _create_participants(
        self,
        participant_client: OpenAIChatClient,
        tools: Iterable[MCPStreamableHTTPTool] | None,
    ) -> Dict[str, FrameworkAgent]:
        # Get base MCP tool (connect once, filter per agent)
        base_mcp_tool = tools[0] if tools else None
        logger.info(f"[MCP PARTICIPANTS] Creating participants with base MCP tool: {base_mcp_tool}")
        
        # CRITICAL: Connect to MCP server BEFORE filtering to load all available tools
        if base_mcp_tool:
            await base_mcp_tool.__aenter__()
            logger.info(f"[MCP PARTICIPANTS] Connected to MCP server, loaded {len(base_mcp_tool.functions)} tools")
        
        base_definitions: Dict[str, Dict[str, Any]] = {
            "crm_billing": {
                "name": "crm_billing",
                "description": (
                    "Agent specializing in customer account, subscription, billing inquiries, invoices, payments, and related policy checks."
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
                    "You are the CRM & Billing **internal specialist**.\n"
                    "**CRITICAL: You communicate ONLY with the orchestrator, NOT directly with the customer.**\n"
                    "**CRITICAL: You MUST use your tools to retrieve factual data. NEVER guess or hallucinate information.**\n"
                    "- For ANY customer-specific question, call the appropriate tool (get_customer_detail, get_billing_summary, etc.).\n"
                    "- If you don't have necessary identifiers (customer ID, email, phone), inform the orchestrator: "
                    "'I need the customer ID, email, or phone number to retrieve this information.'\n"
                    "- Query structured CRM / billing systems for account, subscription, invoice, and payment information.\n"
                    "- Cross-check Knowledge Base articles on billing policies, payment processing, refund rules, and compliance.\n"
                    "- Reply to the orchestrator with concise, structured information and flag any policy concerns you detect.\n"
                    "- Explicitly cite the tool results (customer ID, invoice numbers, amounts, timestamps) that back your answer.\n"
                    "- If no tool can answer the question, state 'I cannot answer this without the appropriate tool' instead of guessing.\n"
                    "**Remember: The orchestrator will translate your response into customer-friendly language. Focus on accuracy and completeness.**"
                ),
            },
            "product_promotions": {
                "name": "product_promotions",
                "description": (
                    "Agent for retrieving and explaining product availability, promotions, discounts, eligibility, and terms."
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
                    "You are the Product & Promotions **internal specialist**.\n"
                    "**CRITICAL: You communicate ONLY with the orchestrator, NOT directly with the customer.**\n"
                    "**CRITICAL: You MUST use your tools to retrieve factual data. NEVER guess or hallucinate information.**\n"
                    "- For ANY product or promotion question, call the appropriate tool (get_products, get_promotions, get_eligible_promotions, etc.).\n"
                    "- If you need more information (customer ID for eligibility, product category, etc.), inform the orchestrator: "
                    "'I need the customer ID to check promotion eligibility.'\n"
                    "- Retrieve promotional offers, product availability, eligibility criteria, and discount information from structured sources.\n"
                    "- Cross-reference Knowledge Base FAQs, terms & conditions, and best practices in every response.\n"
                    "- Provide factual, up-to-date product/promo details to the orchestrator, citing the tool outputs or documents you referenced.\n"
                    "- If no tool can answer the question, state 'I cannot answer this without the appropriate tool' instead of guessing.\n"
                    "**Remember: The orchestrator will translate your response into customer-friendly language. Focus on accuracy and completeness.**"
                ),
            },
            "security_authentication": {
                "name": "security_authentication",
                "description": (
                    "Agent focusing on security incidents, authentication issues, lockouts, and risk mitigation guidance."
                ),
                "tools": [
                    "get_security_logs",
                    "unlock_account",
                    "get_support_tickets",
                    "create_support_ticket",
                    "search_knowledge_base",
                ],
                "instructions": (
                    "You are the Security & Authentication **internal specialist**.\n"
                    "**CRITICAL: You communicate ONLY with the orchestrator, NOT directly with the customer.**\n"
                    "**CRITICAL: You MUST use your tools to retrieve factual data. NEVER guess or hallucinate information.**\n"
                    "- For ANY security or authentication question, call the appropriate tool (get_security_logs, unlock_account, etc.).\n"
                    "- If you need more information (customer ID, account details, etc.), inform the orchestrator: "
                    "'I need the customer ID to retrieve security logs.'\n"
                    "- Investigate authentication logs, account lockouts, and security incidents using your tools.\n"
                    "- Always cross-reference Knowledge Base security policies and troubleshooting guides.\n"
                    "- Return clear risk assessments, list the log entries or tool findings you relied on, and recommend remediation steps grounded in those outputs.\n"
                    "- If no tool can answer the question, state 'I cannot answer this without the appropriate tool' instead of guessing."
                ),
            },
        }

        participants: Dict[str, FrameworkAgent] = {}
        for participant_id, defaults in base_definitions.items():
            agent_kwargs: Dict[str, Any] = {
                **defaults,
                "client": participant_client,
                "default_options": ChatOptions(model=self.azure_deployment),
            }
            
            # Apply tool filtering for this participant's domain
            if base_mcp_tool is not None and "tools" in defaults:
                filtered_tools = create_filtered_tool_list(
                    base_mcp_tool=base_mcp_tool,
                    allowed_tool_names=defaults["tools"],
                    agent_name=participant_id
                )
                if filtered_tools:
                    agent_kwargs["tools"] = filtered_tools
                    logger.info(f"[MCP PARTICIPANTS] Assigned {len(filtered_tools)} filtered tools to agent '{participant_id}'")
            elif base_mcp_tool is not None and "tools" not in agent_kwargs:
                # Fallback: if no tool list defined, give all tools
                agent_kwargs["tools"] = base_mcp_tool
                logger.warning(f"[MCP PARTICIPANTS] No tool filter for '{participant_id}', using all tools")

            merged_kwargs = self._apply_participant_overrides(participant_id, agent_kwargs)
            agent = FrameworkAgent(**merged_kwargs)
            
            # Initialize agent session (MCP tool already connected above)
            await agent.__aenter__()
            logger.info(f"[MCP PARTICIPANTS] Initialized agent session for '{participant_id}'")
            
            participants[participant_id] = agent

        return participants

    def _apply_participant_overrides(self, participant_id: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
        overrides = self._participant_overrides.get(participant_id, {})
        if not overrides:
            return defaults

        merged = {**defaults, **overrides}

        if overrides.get("tools") == "inherit":
            merged["tools"] = defaults.get("tools")

        return merged

    async def _run_workflow(
        self,
        workflow: Any,
        checkpoint_storage: CheckpointStorage,
        task: str | None,
        checkpoint_id: str | None = None,
    ) -> str | None:
        final_answer: str | None = None

        try:
            # Start the initial stream using the new run() API with stream=True
            run_kwargs: Dict[str, Any] = {"stream": True}
            if checkpoint_id:
                run_kwargs["checkpoint_id"] = checkpoint_id
                run_kwargs["checkpoint_storage"] = checkpoint_storage
            
            if task is not None:
                response_stream = workflow.run(task, **run_kwargs)
            else:
                response_stream = workflow.run(**run_kwargs)

            pending_responses: dict[str, Any] | None = None
            output_received = False

            while not output_received:
                # If we have pending plan-review responses, resume via run() with responses
                if pending_responses is not None:
                    response_stream = workflow.run(stream=True, responses=pending_responses)
                    pending_responses = None

                pending_request: WorkflowEvent | None = None

                async for event in response_stream:
                    # Stream events to WebSocket if available
                    await self._process_workflow_event(event)

                    if event.type == "output":
                        final_answer = self._extract_text_from_event(event)
                        output_received = True

                    elif event.type == "request_info" and event.request_type is MagenticPlanReviewRequest:
                        # Capture plan review request — stream will pause after this
                        pending_request = event

                # Handle plan review: auto-approve and loop back
                if pending_request is not None and not output_received:
                    request_data = cast(MagenticPlanReviewRequest, pending_request.data)
                    logger.info(
                        "[AgentFramework-Magentic] Plan review requested (stalled=%s) — auto-approving",
                        request_data.is_stalled,
                    )

                    # Broadcast plan-review approval to WebSocket
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "orchestrator",
                                "kind": "plan_review_approved",
                                "content": "Plan auto-approved. Continuing execution...",
                            },
                        )

                    response = request_data.approve()
                    pending_responses = {pending_request.request_id: response}
                    pending_request = None
                elif not output_received and pending_request is None:
                    # Stream ended without output and no plan review request — unexpected
                    logger.warning("[AgentFramework-Magentic] workflow stream ended without output or plan review")
                    break

        except Exception as exc:
            logger.error("[AgentFramework-Magentic] workflow failure: %s", exc, exc_info=True)
            return None

        return final_answer

    async def _process_workflow_event(self, event: WorkflowEvent) -> None:
        """Process workflow events and stream to WebSocket clients.
        
        In agent-framework 1.2.x, all events are WorkflowEvent with a .type field:
        - 'magentic_orchestrator': plan, replan, progress ledger updates
        - 'request_info': plan review requests
        - 'data': streaming tokens from participant agents
        - 'executor_completed': complete agent response
        - 'output': final workflow output
        """
        if not self._ws_manager:
            # Just log if no WebSocket manager
            if self._workflow_event_logging_enabled:
                await self._log_workflow_event(event)
            return

        try:
            # Handle MagenticOrchestratorEvent (plan, replan, progress ledger)
            if event.type == "magentic_orchestrator" and isinstance(event.data, MagenticOrchestratorEvent):
                orch_event = event.data
                message_text = getattr(orch_event.content, "text", "") or str(orch_event.content)
                kind = orch_event.event_type.value  # e.g. "plan_created", "replanned", "progress_ledger_updated"
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "orchestrator",
                        "kind": kind,
                        "content": message_text,
                    },
                )

            # Handle plan review requests
            elif event.type == "request_info" and event.request_type is MagenticPlanReviewRequest:
                request_data = cast(MagenticPlanReviewRequest, event.data)
                plan_text = getattr(request_data.plan, "text", "") or str(request_data.plan) if hasattr(request_data, "plan") else str(request_data)
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "orchestrator",
                        "kind": "plan_review_requested",
                        "content": plan_text,
                        "is_stalled": request_data.is_stalled,
                    },
                )

            # Handle streaming tokens from participant agents (data events)
            elif event.type == "data" and event.data:
                agent_id = event.executor_id

                if self._stream_agent_id != agent_id or not self._stream_line_open:
                    self._stream_agent_id = agent_id
                    self._stream_line_open = True
                    await self._ws_manager.broadcast(
                        self.session_id,
                        {
                            "type": "agent_start",
                            "agent_id": agent_id,
                            "show_message_in_internal_process": True,
                        },
                    )

                # Stream text tokens
                text = getattr(event.data, "text", "") or ""
                if text:
                    await self._ws_manager.broadcast(
                        self.session_id,
                        {
                            "type": "agent_token",
                            "agent_id": agent_id,
                            "content": text,
                        },
                    )
            
            # Handle complete agent response (executor_completed events)
            elif event.type == "executor_completed" and event.data:
                if self._stream_line_open:
                    self._stream_line_open = False
                
                agent_id = event.executor_id
                message_text = getattr(event.data, "text", "") or ""
                role = getattr(event.data, "role", None)
                
                # Store last agent message for deduplication with final result
                self._last_agent_message = message_text
                
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "agent_message",
                        "agent_id": agent_id,
                        "role": role.value if role else "assistant",
                        "content": message_text,
                    },
                )
            
            # Handle final workflow output
            elif event.type == "output":
                final_text = self._extract_text_from_event(event)
                cleaned_final_text = self._sanitize_final_answer(final_text) or final_text
                
                # Only send if different from the last agent message
                if final_text != self._last_agent_message:
                    await self._ws_manager.broadcast(
                        self.session_id,
                        {
                            "type": "final_result",
                            "content": cleaned_final_text,
                        },
                    )
                else:
                    logger.info("[STREAMING] Skipping duplicate final_result (same as last agent_message)")
                
                # Reset for next request
                self._last_agent_message = None

        except Exception as exc:
            logger.error("[AgentFramework-Magentic] Failed to process event: %s", exc, exc_info=True)

    @staticmethod
    def _extract_text_from_event(event: WorkflowEvent) -> str:
        """Extract text content from a WorkflowEvent with type='output'.
        
        Handles various data formats:
        - Single Message object with .text attribute
        - List of Message objects
        - AgentResponse with .text attribute
        - Plain string
        """
        data = event.data
        
        # Handle list of messages (common for Magentic workflow output)
        if isinstance(data, list):
            texts = []
            for item in data:
                if hasattr(item, "text") and getattr(item, "text"):
                    texts.append(str(getattr(item, "text")))
                elif isinstance(item, str):
                    texts.append(item)
            if texts:
                return "\n".join(texts)
            # Fallback: stringify the list
            return str(data)
        
        # Handle single object with text attribute
        if hasattr(data, "text") and getattr(data, "text"):
            return str(getattr(data, "text"))
        
        # Handle AgentRunResponse which may have messages
        if hasattr(data, "messages") and getattr(data, "messages"):
            messages = getattr(data, "messages")
            if isinstance(messages, list):
                texts = []
                for msg in messages:
                    if hasattr(msg, "text") and getattr(msg, "text"):
                        texts.append(str(getattr(msg, "text")))
                if texts:
                    return "\n".join(texts)
        
        # Fallback: convert to string
        return str(data)

    async def _log_workflow_event(self, event: WorkflowEvent) -> None:
        if event.type == "output":
            logger.debug("[AgentFramework-Magentic] Workflow output event: %s", event.data)
        else:
            logger.debug("[AgentFramework-Magentic] Workflow event emitted: type=%s, executor=%s", event.type, event.executor_id)

    def _render_task_with_history(self, prompt: str) -> str:
        if not self.chat_history:
            return prompt

        formatted_turns = []
        for turn in self.chat_history:
            role = turn.get("role", "user").lower()
            speaker = "User" if role == "user" else "Assistant"
            content = turn.get("content", "")
            formatted_turns.append(f"{speaker}: {content}")

        formatted_turns.append(f"User: {prompt}")
        formatted_turns.append(
            "System: Provide an updated response that respects the prior conversation while focusing on the latest user message."
        )
        return "\n".join(formatted_turns)

    def _sanitize_final_answer(self, final_answer: Optional[str]) -> Optional[str]:
        """Remove FINAL_ANSWER prefix from workflow output."""
        if not final_answer:
            return None

        # Try all known marker variations
        for marker in ["FINAL_ANSWER:", "FINAL ANSWER:", "FINALANSWER:"]:
            if marker in final_answer:
                return final_answer.split(marker, maxsplit=1)[-1].strip()

        # No marker found - return cleaned text
        return final_answer.strip() or None

    def _create_checkpoint_storage(self) -> CheckpointStorage:
        """Resolve the active checkpoint storage for this session.

        Resolution order:

        1. An explicit per-process override (set by tests or hosts that wire
           up a custom storage via ``state_store["magentic_checkpoint_storage"]``).
        2. A factory callable supplied via constructor or
           ``state_store["magentic_checkpoint_storage_factory"]``.
        3. The standard built-in storages exposed by
           ``checkpoint_storage.create_checkpoint_storage`` (in-memory by
           default; FileCheckpointStorage / CosmosCheckpointStorage when
           ``WORKFLOW_CHECKPOINT_BACKEND`` is set).
        """
        if self._checkpoint_storage_override is not None:
            return self._checkpoint_storage_override

        if self._checkpoint_storage_factory:
            # The legacy factory signature passed (state_dict, session_id);
            # preserve it so existing hosts continue to work.
            storage_candidate: Any = self._checkpoint_storage_factory({}, self.session_id)
            storage = _coerce_checkpoint_storage(storage_candidate)
            if storage is not None:
                if self._config.get("cache_factory_storage", True):
                    self.state_store["magentic_checkpoint_storage"] = storage
                    self._checkpoint_storage_override = storage
                return storage
            logger.warning(
                "[AgentFramework-Magentic] Provided checkpoint storage factory returned an "
                "object that does not implement CheckpointStorage; falling back to built-in storage."
            )

        return create_checkpoint_storage(self.session_id)

    def _load_effective_config(self, runtime_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        env_config = self._load_env_config()
        if env_config:
            merged.update(env_config)

        store_config = self.state_store.get("magentic_config")
        if isinstance(store_config, dict):
            merged.update(store_config)

        if runtime_config:
            merged.update(runtime_config)

        return merged

    def _load_env_config(self) -> Dict[str, Any]:
        env_config: Dict[str, Any] = {}

        manager_instructions = os.getenv("MAGENTIC_MANAGER_INSTRUCTIONS")
        if manager_instructions:
            env_config["manager_instructions"] = manager_instructions.strip()

        max_rounds = self._maybe_parse_int(os.getenv("MAGENTIC_MAX_ROUNDS"))
        if max_rounds is not None:
            env_config["max_round_count"] = max_rounds

        max_stalls = self._maybe_parse_int(os.getenv("MAGENTIC_MAX_STALLS"))
        if max_stalls is not None:
            env_config["max_stall_count"] = max_stalls

        max_resets = self._maybe_parse_int(os.getenv("MAGENTIC_MAX_RESETS"))
        if max_resets is not None:
            env_config["max_reset_count"] = max_resets

        log_events = self._maybe_parse_bool(os.getenv("MAGENTIC_LOG_WORKFLOW_EVENTS"))
        if log_events is not None:
            env_config["log_workflow_events"] = log_events

        plan_review = self._maybe_parse_bool(os.getenv("MAGENTIC_ENABLE_PLAN_REVIEW"))
        if plan_review is not None:
            env_config["enable_plan_review"] = plan_review

        mcp_timeout = self._maybe_parse_int(os.getenv("MAGENTIC_MCP_TIMEOUT_SECONDS"))
        if mcp_timeout is not None:
            env_config["mcp_timeout_seconds"] = mcp_timeout

        mcp_request_timeout = self._maybe_parse_int(os.getenv("MAGENTIC_MCP_REQUEST_TIMEOUT_SECONDS"))
        if mcp_request_timeout is not None:
            env_config["mcp_request_timeout_seconds"] = mcp_request_timeout

        mcp_retry_attempts = self._maybe_parse_int(os.getenv("MAGENTIC_MCP_STARTUP_RETRIES"))
        if mcp_retry_attempts is not None:
            env_config["mcp_startup_retries"] = mcp_retry_attempts

        mcp_retry_backoff = os.getenv("MAGENTIC_MCP_RETRY_BACKOFF_SECONDS")
        if mcp_retry_backoff is not None:
            try:
                env_config["mcp_retry_backoff_seconds"] = float(mcp_retry_backoff)
            except ValueError:
                logger.warning(
                    "[AgentFramework-Magentic] Invalid MAGENTIC_MCP_RETRY_BACKOFF_SECONDS value '%s'; expecting float.",
                    mcp_retry_backoff,
                )

        mcp_headers_raw = os.getenv("MAGENTIC_MCP_HEADERS")
        if mcp_headers_raw:
            try:
                parsed_headers = json.loads(mcp_headers_raw)
                if isinstance(parsed_headers, dict):
                    env_config["mcp_headers"] = parsed_headers
            except json.JSONDecodeError:
                logger.warning(
                    "[AgentFramework-Magentic] Failed to parse MAGENTIC_MCP_HEADERS as JSON; ignoring value.",
                    exc_info=True,
                )

        return env_config

    @staticmethod
    async def _call_maybe_async(fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Call a function that might be sync or async."""
        result = fn(*args, **kwargs)
        return await result if inspect.isawaitable(result) else result

    def _maybe_parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse string to int, return None if invalid."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _maybe_parse_bool(self, value: Optional[str]) -> Optional[bool]:
        """Parse string to bool, return None if invalid."""
        if not value:
            return None
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return None

    def _mark_pending_prompt(self, prompt: str) -> None:
        """Persist the in-flight prompt so a resume after a crash can re-emit it."""
        self.state_store[self._pending_prompt_state_key] = prompt

    def _consume_pending_prompt(self) -> Optional[str]:
        """Pop and return the previously-stored in-flight prompt, if any."""
        return self.state_store.pop(self._pending_prompt_state_key, None)

    def _current_workflow_name(self) -> Optional[str]:
        """Return the workflow name recorded by the most recent build, if any."""
        return self.state_store.get(self._workflow_name_state_key)

    async def _reset_checkpoint_progress(self, storage: CheckpointStorage) -> None:
        """Wipe checkpoints for the active workflow and clear the pending prompt."""
        await purge_checkpoints(storage, self._current_workflow_name())
        self.state_store.pop(self._pending_prompt_state_key, None)

    async def _get_latest_checkpoint_id(self, storage: CheckpointStorage) -> Optional[str]:
        """Resolve the most recent checkpoint ID using only the public 1.2.x protocol."""
        workflow_name = self._current_workflow_name()
        if not workflow_name:
            return None
        try:
            latest = await storage.get_latest(workflow_name=workflow_name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("get_latest failed for workflow %s: %s", workflow_name, exc)
            return None
        if latest is None:
            return None
        checkpoint_id = getattr(latest, "checkpoint_id", None)
        return checkpoint_id if isinstance(checkpoint_id, str) else None
