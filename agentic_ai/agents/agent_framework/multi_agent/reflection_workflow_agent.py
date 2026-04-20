"""
Reflection Workflow Agent with Skills — SequentialBuilder-based variant of reflection_agent.py.

Uses the SequentialBuilder orchestration from the Agent Framework documentation:
  https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential

Key additions over reflection_agent.py:
  1. SequentialBuilder workflow instead of imperative loop.
  2. SkillRegistry selects the best-matching domain skill per request.
  3. Skill instructions replace the generic primary agent prompt → smaller context.
  4. FilteredMCPTool exposes ONLY the tools declared by that skill → better precision.
  5. get_skill_info() exposes skill metadata for evaluation metrics.

Pipeline (single round):
  PrimaryAgent (skill-scoped) → Reviewer → RefineExecutor (skill-scoped)

  - Same BaseAgent / ToolCallTrackingMixin / state management as reflection_agent.py.
"""

import logging
from typing import Any, Dict, List, Optional

from agent_framework import (
    AgentExecutorResponse,
    AgentRunEvent,
    ChatAgent,
    ChatMessage,
    Executor,
    ExecutorCompletedEvent,
    ExecutorInvokedEvent,
    MCPStreamableHTTPTool,
    SequentialBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient

from agents.base_agent import BaseAgent, ToolCallTrackingMixin
from agents.agent_framework.skills import Skill, SkillRegistry
from agents.agent_framework.utils import create_filtered_tool_list

logger = logging.getLogger(__name__)

# ── Instructions ────────────────────────────────────────────────────────────
# PRIMARY_AGENT_INSTRUCTIONS removed — now provided by SkillRegistry per request.

REVIEWER_INSTRUCTIONS = (
    "You are a quality assurance reviewer for customer support responses. "
    "Review responses for: 1) Accuracy, 2) Completeness, 3) Professional tone, 4) Proper tool usage. "
    "If the response meets quality standards, respond with exactly 'APPROVE'. "
    "If improvements are needed, provide specific, constructive feedback."
)

REFINE_INSTRUCTIONS = (
    "You are a helpful customer support assistant for Contoso company. "
    "You will receive a conversation containing a user question, a primary response, "
    "and reviewer feedback. If the reviewer approved the response, output the primary "
    "response unchanged. Otherwise, produce an improved response that addresses the "
    "reviewer's feedback. Provide only the improved response, no meta-commentary."
)

AGENT_NAMES = {
    "primary_agent": "Primary Agent",
    "reviewer_agent": "Quality Reviewer",
}


# ── Custom Executor: Refine step ────────────────────────────────────────────


class RefineExecutor(Executor):
    """Conditionally refines the response based on the reviewer's feedback.

    Receives the full conversation (list[ChatMessage]) from the SequentialBuilder
    pipeline via AgentExecutorResponse.  When the last assistant message from
    the reviewer contains 'APPROVE', it passes the conversation through
    unchanged.  Otherwise it invokes a refine agent to improve the primary
    response based on the reviewer feedback.
    """

    def __init__(
        self,
        chat_client: AzureOpenAIChatClient,
        model: str,
        filtered_tools: List[Any] | None,
        id: str = "refine_executor",
    ) -> None:
        super().__init__(id=id)
        self._chat_client = chat_client
        self._model = model
        self._filtered_tools = filtered_tools
        self._agent: ChatAgent | None = None

    async def _ensure_agent(self) -> None:
        if self._agent is not None:
            return
        self._agent = ChatAgent(
            name="Refiner",
            chat_client=self._chat_client,
            instructions=REFINE_INSTRUCTIONS,
            tools=self._filtered_tools,
            model=self._model,
        )
        await self._agent.__aenter__()
        logger.info("[RefineExecutor] Agent initialised")

    @handler
    async def handle_conversation(
        self,
        agent_response: AgentExecutorResponse,
        ctx: WorkflowContext[list[ChatMessage]],
    ) -> None:
        conversation: list[ChatMessage] = list(agent_response.full_conversation)

        # Find the reviewer's last assistant message
        reviewer_text = ""
        for msg in reversed(conversation):
            if msg.role.value == "assistant":
                reviewer_text = msg.text or ""
                break

        if "APPROVE" in reviewer_text.upper():
            logger.info("[RefineExecutor] Reviewer approved — surfacing primary response")
            # Find the primary agent's last non-empty response (skip tool-call messages)
            primary_text = ""
            for msg in conversation:
                if msg.role.value == "assistant" and msg.author_name != "Reviewer":
                    text = msg.text or ""
                    if text.strip():
                        primary_text = text
            # Re-append primary response so it's the last assistant message
            conversation.append(
                ChatMessage(role="assistant", text=primary_text, author_name="FinalResponse")
            )
            await ctx.send_message(conversation)
            return

        logger.info("[RefineExecutor] Reviewer rejected — refining response")
        await self._ensure_agent()
        assert self._agent is not None

        # Build a refine prompt from the conversation context
        user_question = ""
        primary_response = ""
        for msg in conversation:
            if msg.role.value == "user" and not user_question:
                user_question = msg.text or ""
            elif msg.role.value == "assistant" and msg.author_name != "Reviewer":
                text = msg.text or ""
                if text.strip():
                    primary_response = text

        refine_prompt = (
            f"Improve this customer support response based on reviewer feedback:\n\n"
            f"**Original Question:** {user_question}\n\n"
            f"**Primary Response:** {primary_response}\n\n"
            f"**Reviewer Feedback:** {reviewer_text}\n\n"
            f"Provide only the improved response, no meta-commentary."
        )

        thread = self._agent.get_new_thread()
        parts: List[str] = []
        async for chunk in self._agent.run_stream(refine_prompt, thread=thread):
            if hasattr(chunk, "text") and chunk.text:
                parts.append(chunk.text)

        refined = "".join(parts)
        logger.info(f"[RefineExecutor] Refined response length: {len(refined)} chars")

        # Append refined response as the final assistant message
        conversation.append(ChatMessage(role="assistant", text=refined, author_name="Refiner"))
        await ctx.send_message(conversation)


# ── Workflow-based Agent class (same base as reflection_agent.py) ────────────


class Agent(ToolCallTrackingMixin, BaseAgent):
    """Skill-routed reflection agent implemented as a SequentialBuilder workflow.

    On the first request:
      1. SkillRegistry.select(prompt) picks the best-matching Skill.
      2. skill.build_instructions() becomes the primary agent's system prompt.
      3. create_filtered_tool_list() exposes ONLY the skill's allowed tools.
      4. SequentialBuilder wires: PrimaryAgent → Reviewer → RefineExecutor.

    Everything else (state management, streaming, BaseAgent) is identical to
    reflection_agent.py so results are directly comparable.
    """

    def __init__(
        self,
        state_store: Dict[str, Any],
        session_id: str,
        access_token: str | None = None,
    ) -> None:
        super().__init__(state_store, session_id)
        self._access_token = access_token
        self._ws_manager = None
        self._workflow = None
        self._initialized = False
        self._active_skill: Optional[Skill] = None
        self._skill_confidence: float = 0.0
        self.init_tool_tracking()
        logger.info(f"[ReflectionWorkflow] Initialised session: {session_id}")

    def set_websocket_manager(self, manager: Any) -> None:
        self._ws_manager = manager

    # ── helpers ──────────────────────────────────────────────────────────

    async def _broadcast(self, kind: str, content: str, **extra: Any) -> None:
        if self._ws_manager:
            message = {"type": "orchestrator", "kind": kind, "content": content, **extra}
            await self._ws_manager.broadcast(self.session_id, message)

    async def _broadcast_raw(self, message: Dict[str, Any]) -> None:
        if self._ws_manager:
            await self._ws_manager.broadcast(self.session_id, message)

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _connect_base_mcp_tool(self, headers: Dict[str, str]) -> MCPStreamableHTTPTool | None:
        """Connect the base MCP tool (all tools loaded) so we can filter it."""
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI not configured")
            return None
        tool = MCPStreamableHTTPTool(
            name="mcp-streamable",
            url=self.mcp_server_uri,
            headers=headers,
            timeout=30,
            request_timeout=30,
        )
        await tool.__aenter__()
        return tool

    # ── setup (requires prompt for skill selection) ──────────────────────

    async def _setup(self, prompt: str) -> None:
        if self._initialized:
            return

        # 1. Select skill
        skill, confidence = SkillRegistry.select(prompt)
        self._active_skill = skill
        self._skill_confidence = confidence
        logger.info(
            f"[Skills] Active skill: '{skill.name}' "
            f"({skill.display_name}) confidence={confidence:.2f} "
            f"tools={skill.allowed_tools}"
        )

        # 2. Validate Azure config
        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError("Azure OpenAI configuration incomplete.")
        if not self.azure_openai_key and not self.azure_credential:
            raise RuntimeError("Azure OpenAI authentication not configured.")

        client_kwargs: Dict[str, Any] = {
            "deployment_name": self.azure_deployment,
            "endpoint": self.azure_openai_endpoint,
            "api_version": self.api_version,
        }
        if self.azure_openai_key:
            client_kwargs["api_key"] = self.azure_openai_key
        else:
            client_kwargs["credential"] = self.azure_credential

        chat_client = AzureOpenAIChatClient(**client_kwargs)

        # 3. Build filtered tool list (only the skill's allowed tools)
        headers = self._build_headers()
        base_mcp_tool = await self._connect_base_mcp_tool(headers)
        filtered_functions = create_filtered_tool_list(
            base_mcp_tool,
            skill.allowed_tools,
            agent_name=f"reflection-skills-{skill.name}",
        )

        # 4. Create agents with skill instructions + filtered tools
        primary = ChatAgent(
            name=f"PrimaryAgent_skills_{skill.name}",
            chat_client=chat_client,
            instructions=skill.build_instructions(),
            tools=filtered_functions,
            model=self.openai_model_name,
        )

        reviewer = ChatAgent(
            name="Reviewer",
            chat_client=chat_client,
            instructions=REVIEWER_INSTRUCTIONS,
            tools=filtered_functions,
            model=self.openai_model_name,
        )

        # Custom executor for conditional refine (skill-filtered tools)
        refiner = RefineExecutor(chat_client, self.openai_model_name, filtered_functions)

        # 5. Build sequential workflow: Primary → Reviewer → Refine
        self._workflow = (
            SequentialBuilder()
            .participants([primary, reviewer, refiner])
            .build()
        )

        self._initialized = True
        logger.info(
            f"[ReflectionWorkflow] Workflow built: "
            f"Primary({skill.name}) → Reviewer → Refine"
        )

    # ── chat entry point ─────────────────────────────────────────────────

    async def chat_async(self, prompt: str) -> str:
        await self._setup(prompt)
        if not self._workflow:
            raise RuntimeError("Workflow failed to initialize.")

        self.clear_tool_calls()

        skill_label = self._active_skill.display_name if self._active_skill else "General"
        await self._broadcast(
            "plan",
            f"🔄 Reflection Workflow (Skill: {skill_label})\n\n"
            f"Primary Agent → Reviewer → Refine (if needed)…",
        )

        await self._broadcast("step", f"🤖 **Primary Agent** ({skill_label}) generating response…")
        final_response = ""

        async for event in self._workflow.run_stream(prompt):
            # WorkflowOutputEvent carries the final conversation (list[ChatMessage])
            if isinstance(event, WorkflowOutputEvent):
                conversation = event.data
                if conversation:
                    # Last non-empty assistant message is the final response
                    for msg in reversed(conversation):
                        if msg.role.value == "assistant":
                            text = msg.text or ""
                            if text.strip():
                                final_response = text
                                break

            # Capture function calls fired inside ChatAgent participants.
            # AgentRunEvent fires once per participant completion with the full
            # AgentResponse — iterate its messages for function_call content items.
            elif isinstance(event, AgentRunEvent):
                response = event.data
                for msg in getattr(response, "messages", None) or []:
                    for content in getattr(msg, "contents", None) or []:
                        if getattr(content, "type", None) == "function_call":
                            args = content.arguments
                            if isinstance(args, str):
                                import json
                                try:
                                    args = json.loads(args) if args else {}
                                except Exception:
                                    args = {"_raw": args[:200]}
                            self.add_tool_call(content.name or "<unknown>", args or {})

            # Broadcast executor lifecycle events for the UI
            if isinstance(event, ExecutorInvokedEvent):
                eid = event.executor_id
                if "Reviewer" in eid:
                    await self._broadcast("step", "🔍 **Reviewer** evaluating response…")
                elif "refine" in eid:
                    await self._broadcast("step", "🔄 **Refiner** improving response…")
            elif isinstance(event, ExecutorCompletedEvent):
                eid = event.executor_id
                if "Reviewer" in eid:
                    await self._broadcast("step", "✅ Review complete")

        if not final_response:
            final_response = "(No response produced by workflow)"

        await self._broadcast(
            "result",
            "✅ Reflection Complete\n\nFinal response delivered with quality assurance!",
        )
        await self._broadcast_raw({"type": "final_result", "content": final_response})

        # Persist state (same as reflection_agent.py)
        self.append_to_chat_history([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": final_response},
        ])

        return final_response

    # ── Metrics helper (used by eval script) ─────────────────────────────

    def get_skill_info(self) -> Dict[str, Any]:
        """Return active skill metadata for eval metrics."""
        if not self._active_skill:
            return {}
        return {
            "skill_name": self._active_skill.name,
            "skill_display_name": self._active_skill.display_name,
            "confidence": self._skill_confidence,
            "allowed_tools": self._active_skill.allowed_tools,
            "instruction_chars": len(self._active_skill.build_instructions()),
        }
