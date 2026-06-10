import logging
from typing import Any, Dict, List

from agent_framework import Agent as FrameworkAgent, AgentSession, ChatOptions, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient

from agents.base_agent import BaseAgent, ToolCallTrackingMixin

logger = logging.getLogger(__name__)


class Agent(ToolCallTrackingMixin, BaseAgent):
    """Agent Framework implementation of a single assistant loop."""

    def __init__(self, state_store: Dict[str, Any], session_id: str, access_token: str | None = None) -> None:
        super().__init__(state_store, session_id)
        self._agent: FrameworkAgent | None = None
        self._session: AgentSession | None = None
        self._initialized = False
        self._access_token = access_token
        self._ws_manager = None  # WebSocket manager for streaming
        # Track conversation turn for tool call grouping - load from state store
        self._turn_key = f"{session_id}_current_turn"
        self._current_turn = state_store.get(self._turn_key, 0)
        # Initialize tool tracking from mixin
        self.init_tool_tracking()

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager
        logger.info(f"[STREAMING] WebSocket manager set for single_agent, session_id={self.session_id}")

    async def _setup_single_agent(self) -> None:
        if self._initialized:
            return

        # Check for either API key OR credential-based authentication
        has_api_key = bool(self.azure_openai_key)
        has_credential = bool(self.azure_credential)
        
        if not all([self.azure_deployment, self.azure_openai_endpoint]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure "
                "AZURE_OPENAI_CHAT_DEPLOYMENT and AZURE_OPENAI_ENDPOINT are set."
            )
        
        if not has_api_key and not has_credential:
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Either set AZURE_OPENAI_API_KEY "
                "or ensure managed identity is available for credential-based authentication."
            )

        headers = self._build_headers()
        mcp_tools = await self._maybe_create_tools(headers)

        # Use API key if available, otherwise use credential-based authentication
        if has_api_key:
            chat_client = OpenAIChatClient(
                api_key=self.azure_openai_key,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
            )
            logger.info("[AgentFramework] Using API key authentication for Azure OpenAI")
        else:
            chat_client = OpenAIChatClient(
                credential=self.azure_credential,
                model=self.azure_deployment,
                azure_endpoint=self.azure_openai_endpoint,
            )
            logger.info("[AgentFramework] Using managed identity authentication for Azure OpenAI")

        instructions = (
            "You are a helpful assistant. You can use multiple tools to find information and answer questions. "
            "Review the tools available to you and use them as needed. You can also ask clarifying questions if "
            "the user is not clear. If customer ask any operations that there's no tool to support, said that you cannot do it. "
            "Never hallunicate any operation that you do not actually do."
        )

        tools = mcp_tools[0] if mcp_tools else None

        self._agent = FrameworkAgent(
            client=chat_client,
            name="ai_assistant",
            instructions=instructions,
            tools=tools,
            default_options=ChatOptions(model=self.azure_deployment),
        )

        try:
            await self._agent.__aenter__()
        except Exception:
            self._agent = None
            raise

        await self._log_mcp_tool_details()

        if self.state:
            self._session = AgentSession.from_dict(self.state)
        else:
            self._session = self._agent.create_session()

        self._initialized = True

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _maybe_create_tools(self, headers: Dict[str, str]) -> List[MCPStreamableHTTPTool] | None:
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

        return [tool]

    async def _log_mcp_tool_details(self) -> None:
        if not self._agent:
            return

        mcp_tools = getattr(self._agent, "_local_mcp_tools", None)
        if not mcp_tools:
            logger.debug("No MCP tools registered on the agent; skipping tool inspection.")
            return

        mcp_tool = mcp_tools[0]
        session = getattr(mcp_tool, "session", None)
        if session is None:
            logger.debug("MCP tool session is not available; cannot list tools for debugging.")
            return

        try:
            tool_list = await session.list_tools()
        except Exception as exc:
            logger.exception("Failed to fetch MCP tool metadata: %s", exc)
            return

        if not tool_list or not getattr(tool_list, "tools", None):
            logger.debug("No tools returned from MCP server during inspection.")
            return

    # get_tool_calls() is inherited from ToolCallTrackingMixin

    async def chat_async(self, prompt: str) -> str:
        await self._setup_single_agent()

        if not self._agent or not self._session:
            raise RuntimeError("Agent Framework single agent failed to initialize correctly.")

        # Clear tool calls from previous request (from mixin)
        self.clear_tool_calls()

        # Increment turn counter for this new conversation turn and persist to state store
        self._current_turn += 1
        self.state_store[self._turn_key] = self._current_turn

        # Use streaming if WebSocket manager is available
        if self._ws_manager:
            return await self._chat_async_streaming(prompt)
        
        # Non-streaming path - use run with stream=True to capture tool calls
        full_response = []
        response_stream = self._agent.run(prompt, stream=True, session=self._session)
        async for chunk in response_stream:
            # Extract tool calls from contents
            if hasattr(chunk, 'contents') and chunk.contents:
                for content in chunk.contents:
                    if content.type == "function_call":
                        # Function call chunks come in pieces. Older SDKs sent
                        # the name only on the first chunk; agent-framework >= 1.7
                        # repeats name + a stable call_id on every chunk, so we
                        # de-duplicate on call_id to avoid fragmenting one call
                        # into many malformed ones.
                        if content.name:
                            self.track_function_call_start(
                                content.name, getattr(content, "call_id", None)
                            )

                        # Accumulate arguments
                        args_chunk = getattr(content, 'arguments', '')
                        if args_chunk:
                            self.track_function_call_arguments(args_chunk)
                    
                    elif content.type == "function_result":
                        # Function result means the call is complete
                        self.track_function_result(
                            getattr(content, "call_id", None),
                            getattr(content, "result", None),
                        )
            
            # Extract text
            if hasattr(chunk, 'text') and chunk.text:
                full_response.append(chunk.text)
        
        # Finalize any remaining function call
        self.finalize_tool_tracking()
        
        assistant_response = ''.join(full_response)

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)

        new_state = self._session.to_dict()
        self._setstate(new_state)

        return assistant_response

    async def _chat_async_streaming(self, prompt: str) -> str:
        """Handle chat with streaming support via WebSocket."""
        if not self._agent or not self._session:
            raise RuntimeError("Agent Framework single agent failed to initialize correctly.")

        # Notify UI that agent started - with convention flag
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "agent_start",
                    "agent_id": "single_agent",
                    "show_message_in_internal_process": False,  # Convention: don't show message in left panel
                },
            )
        
        # Stream the response
        full_response = []
        
        try:
            response_stream = self._agent.run(prompt, stream=True, session=self._session)
            async for chunk in response_stream:
                # Process contents in the chunk
                if hasattr(chunk, 'contents') and chunk.contents:
                    for content in chunk.contents:
                        # Handle function calls - accumulate arguments across chunks
                        if content.type == "function_call":
                            if content.name:
                                # Only the first chunk of a given call_id starts a
                                # new call; later chunks just accumulate arguments.
                                is_new_call = self.track_function_call_start(
                                    content.name, getattr(content, "call_id", None)
                                )

                                # Broadcast that a tool is being called (once per call)
                                if is_new_call and self._ws_manager:
                                    await self._ws_manager.broadcast(
                                        self.session_id,
                                        {
                                            "type": "tool_called",
                                            "agent_id": "single_agent",
                                            "tool_name": content.name,
                                            "turn": self._current_turn,
                                        },
                                    )
                            
                            # Accumulate arguments
                            args_chunk = getattr(content, 'arguments', '')
                            if args_chunk:
                                self.track_function_call_arguments(args_chunk)
                        
                        elif content.type == "function_result":
                            # Function completed - finalize and capture result
                            self.track_function_result(
                                getattr(content, "call_id", None),
                                getattr(content, "result", None),
                            )
                
                # Extract text from chunk
                if hasattr(chunk, 'text') and chunk.text:
                    full_response.append(chunk.text)
                    
                    # Broadcast token to WebSocket
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "agent_token",
                                "agent_id": "single_agent",
                                "content": chunk.text,
                            },
                        )
        except Exception as exc:
            logger.error("[STREAMING] Error during single agent streaming: %s", exc, exc_info=True)
            raise
        
        # Finalize any remaining function call
        self.finalize_tool_tracking()

        assistant_response = ''.join(full_response)

        # Send final result
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "final_result",
                    "content": assistant_response,
                },
            )

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)

        new_state = self._session.to_dict()
        self._setstate(new_state)

        return assistant_response
