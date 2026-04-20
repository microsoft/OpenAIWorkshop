"""
Skill-routed single agent — variant of single_agent.py for A/B comparison.

Key differences from the baseline single_agent.py:
  1. SkillRegistry selects the best-matching domain skill per request.
  2. Skill instructions replace the generic system prompt → smaller context.
  3. FilteredMCPTool exposes ONLY the tools declared by that skill → better precision.

This file is intentionally kept parallel to single_agent.py so both can run
side-by-side in evaluations without interfering with each other.
"""

import logging
from typing import Any, Dict, List, Optional

from agent_framework import ChatAgent, AgentThread, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from agents.base_agent import BaseAgent, ToolCallTrackingMixin
from agents.agent_framework.skills import Skill, SkillRegistry
from agents.agent_framework.utils import create_filtered_tool_list

logger = logging.getLogger(__name__)


class Agent(ToolCallTrackingMixin, BaseAgent):
    """
    Skill-routed single agent.

    On the first request the agent:
      1. Calls SkillRegistry.select(prompt) to pick the best-matching Skill.
      2. Uses skill.build_instructions() as the system prompt.
      3. Passes only skill.allowed_tools to the agent via FilteredMCPTool.

    Everything else (streaming, session persistence, tool-call tracking) is
    identical to single_agent.py so results are directly comparable.
    """

    def __init__(self, state_store: Dict[str, Any], session_id: str, access_token: str | None = None) -> None:
        super().__init__(state_store, session_id)
        self._agent: ChatAgent | None = None
        self._thread: AgentThread | None = None
        self._initialized = False
        self._access_token = access_token
        self._ws_manager = None
        self._turn_key = f"{session_id}_current_turn"
        self._current_turn = state_store.get(self._turn_key, 0)
        # Populated after first call to _setup_single_agent
        self._active_skill: Optional[Skill] = None
        self._skill_confidence: float = 0.0
        self.init_tool_tracking()

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager
        logger.info(f"[STREAMING] WebSocket manager set for single_agent_skills, session_id={self.session_id}")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def _setup_single_agent(self, prompt: str) -> None:
        """Initialise agent with skill-selected instructions and filtered tools."""
        if self._initialized:
            return

        # 1. Select skill from registry
        skill, confidence = SkillRegistry.select(prompt)
        self._active_skill = skill
        self._skill_confidence = confidence
        logger.info(
            f"[Skills] Active skill: '{skill.name}' "
            f"({skill.display_name}) confidence={confidence:.2f} "
            f"tools={skill.allowed_tools}"
        )

        # 2. Validate Azure config
        has_api_key = bool(self.azure_openai_key)
        has_credential = bool(self.azure_credential)

        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure "
                "AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, and "
                "AZURE_OPENAI_API_VERSION are set."
            )
        if not has_api_key and not has_credential:
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Either set "
                "AZURE_OPENAI_API_KEY or ensure managed identity is available."
            )

        # 3. Build filtered tool list (only the skill's allowed tools)
        headers = self._build_headers()
        base_mcp_tool = await self._connect_base_mcp_tool(headers)
        filtered_functions = create_filtered_tool_list(
            base_mcp_tool,
            skill.allowed_tools,
            agent_name=f"skills-{skill.name}",
        )

        # 4. Build chat client
        if has_api_key:
            chat_client = AzureOpenAIChatClient(
                api_key=self.azure_openai_key,
                deployment_name=self.azure_deployment,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
            logger.info("[AgentFramework] Using API key authentication for Azure OpenAI")
        else:
            chat_client = AzureOpenAIChatClient(
                credential=self.azure_credential,
                deployment_name=self.azure_deployment,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
            logger.info("[AgentFramework] Using managed identity authentication for Azure OpenAI")

        # 5. Create agent with skill instructions + filtered tools
        self._agent = ChatAgent(
            name=f"ai_assistant_skills_{skill.name}",
            chat_client=chat_client,
            instructions=skill.build_instructions(),
            tools=filtered_functions,
            model=self.openai_model_name,
        )

        try:
            await self._agent.__aenter__()
        except Exception:
            self._agent = None
            raise

        # 6. Restore or create thread
        if self.state:
            self._thread = await self._agent.deserialize_thread(self.state)
        else:
            self._thread = self._agent.get_new_thread()

        self._initialized = True

    # ------------------------------------------------------------------
    # MCP connection helper
    # ------------------------------------------------------------------

    async def _connect_base_mcp_tool(self, headers: Dict[str, str]) -> MCPStreamableHTTPTool | None:
        """Connect the base MCP tool (all tools loaded) so we can filter it."""
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI is not configured; agent will run without MCP tools.")
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

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    # ------------------------------------------------------------------
    # Chat entry point
    # ------------------------------------------------------------------

    async def chat_async(self, prompt: str) -> str:
        await self._setup_single_agent(prompt)

        if not self._agent or not self._thread:
            raise RuntimeError("Agent Framework skill-routed agent failed to initialize correctly.")

        self.clear_tool_calls()
        self._current_turn += 1
        self.state_store[self._turn_key] = self._current_turn

        if self._ws_manager:
            return await self._chat_async_streaming(prompt)

        return await self._chat_async_non_streaming(prompt)

    # ------------------------------------------------------------------
    # Streaming / non-streaming run loops (identical logic to single_agent.py)
    # ------------------------------------------------------------------

    async def _chat_async_non_streaming(self, prompt: str) -> str:
        full_response: List[str] = []
        async for chunk in self._agent.run_stream(prompt, thread=self._thread):
            self._process_chunk(chunk)
            if hasattr(chunk, "text") and chunk.text:
                full_response.append(chunk.text)
        self.finalize_tool_tracking()
        assistant_response = "".join(full_response)
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)
        new_state = await self._thread.serialize()
        self._setstate(new_state)
        return assistant_response

    async def _chat_async_streaming(self, prompt: str) -> str:
        full_response: List[str] = []
        async for chunk in self._agent.run_stream(prompt, thread=self._thread):
            self._process_chunk(chunk)
            if hasattr(chunk, "text") and chunk.text:
                full_response.append(chunk.text)
                await self._ws_manager.broadcast_fragment(chunk.text)
        self.finalize_tool_tracking()
        assistant_response = "".join(full_response)
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)
        new_state = await self._thread.serialize()
        self._setstate(new_state)
        return assistant_response

    def _process_chunk(self, chunk: Any) -> None:
        """Extract tool-call tracking info from a streaming chunk."""
        if not (hasattr(chunk, "contents") and chunk.contents):
            return
        for content in chunk.contents:
            if content.type == "function_call":
                if content.name:
                    self.track_function_call_start(content.name)
                args_chunk = getattr(content, "arguments", "")
                if args_chunk:
                    self.track_function_call_arguments(args_chunk)
            elif content.type == "function_result":
                self.finalize_tool_tracking()

    # ------------------------------------------------------------------
    # Metrics helper (used by eval script)
    # ------------------------------------------------------------------

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
