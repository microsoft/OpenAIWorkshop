import os
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if needed


class ToolCallTrackingMixin:
    """Opt-in mixin that records tool calls made during a request.

    Agents that want per-request tool-call tracking (e.g. for evaluation
    metrics) can inherit from this mixin *before* BaseAgent:

        class Agent(ToolCallTrackingMixin, BaseAgent): ...

    Usage:
        self.init_tool_tracking()            # in __init__
        self.clear_tool_calls()              # start of chat_async
        self.add_tool_call(name, args)       # when a tool invocation is observed
        self.get_tool_calls()                # at the end (list of dicts)
    """

    def init_tool_tracking(self) -> None:
        self._tool_calls: List[Dict[str, Any]] = []
        self._pending_tool_name: Optional[str] = None
        self._pending_tool_args: str = ""

    def clear_tool_calls(self) -> None:
        self._tool_calls = []
        self._pending_tool_name = None
        self._pending_tool_args = ""

    def add_tool_call(self, name: str, args: Optional[Dict[str, Any]] = None) -> None:
        if not hasattr(self, "_tool_calls"):
            self._tool_calls = []
        self._tool_calls.append({"name": name, "args": args or {}})

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        return list(getattr(self, "_tool_calls", []))

    # --- streaming-style helpers (used by agents that receive tool-call
    # deltas across multiple stream chunks) --------------------------------

    def track_function_call_start(self, name: str) -> None:
        """Record that a new function-call chunk sequence has begun."""
        # Flush any previous pending call that wasn't finalized cleanly.
        if getattr(self, "_pending_tool_name", None):
            self._flush_pending_tool_call()
        self._pending_tool_name = name
        self._pending_tool_args = ""

    def track_function_call_arguments(self, args_chunk: str) -> None:
        """Append an argument fragment to the currently pending call."""
        if not hasattr(self, "_pending_tool_args"):
            self._pending_tool_args = ""
        self._pending_tool_args += args_chunk or ""

    def finalize_tool_tracking(self) -> None:
        """Commit the currently pending tool call (if any) to the list."""
        self._flush_pending_tool_call()

    def _flush_pending_tool_call(self) -> None:
        name = getattr(self, "_pending_tool_name", None)
        if not name:
            return
        raw_args = getattr(self, "_pending_tool_args", "") or ""
        parsed: Dict[str, Any]
        if raw_args:
            try:
                import json
                parsed = json.loads(raw_args)
                if not isinstance(parsed, dict):
                    parsed = {"_value": parsed}
            except Exception:
                parsed = {"_raw": raw_args[:200]}
        else:
            parsed = {}
        self.add_tool_call(name, parsed)
        self._pending_tool_name = None
        self._pending_tool_args = ""


class BaseAgent:
    """  
    Base class for all agents.  
    Not intended to be used directly.  
    Handles environment variables, state store, and chat history.  
    """  
  
    def __init__(self, state_store: Dict[str, Any], session_id: str) -> None:
        self.azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")  # May be unused if using Entra ID
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI")
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME")

        self.session_id = session_id
        self.state_store = state_store

        # Lazy Azure credential (used by agents that authenticate via managed
        # identity / Entra ID instead of an API key). Left as None unless
        # key-based auth is absent so that agents requiring a key still fail
        # loudly with a clear message.
        self.azure_credential: Optional[Any] = None
        if not self.azure_openai_key:
            try:
                from azure.identity import DefaultAzureCredential
                self.azure_credential = DefaultAzureCredential()
            except Exception as exc:  # pragma: no cover - optional dep
                logging.debug(f"Could not initialise DefaultAzureCredential: {exc}")

        self.chat_history: List[Dict[str, str]] = self.state_store.get(f"{session_id}_chat_history", [])
        self.state: Optional[Any] = self.state_store.get(session_id, None)
        logging.debug(f"Chat history for session {session_id}: {self.chat_history}")
  
    def _setstate(self, state: Any) -> None:  
        self.state_store[self.session_id] = state  
  
    def append_to_chat_history(self, messages: List[Dict[str, str]]) -> None:  
        self.chat_history.extend(messages)  
        self.state_store[f"{self.session_id}_chat_history"] = self.chat_history  
  
    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events.

        Override in child class if streaming support is needed.
        """
        pass  # Default: no-op for agents that don't support streaming

    def create_azure_openai_chat_client(self):
        """Create an AzureOpenAIChatClient using Entra ID (RBAC).

        This matches the Azure OpenAI "azure_ad_token_provider" pattern from
        the deployment quickstart, so it works even when key-based auth is
        disabled at the resource level.
        """
        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure AZURE_OPENAI_CHAT_DEPLOYMENT, "
                "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set."
            )

        # Lazy imports to avoid hard dependency if agents aren't used
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from agent_framework.azure import AzureOpenAIChatClient

        # Use the same scope as the official Azure OpenAI Entra ID samples
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

        return AzureOpenAIChatClient(
            deployment_name=self.azure_deployment,
            endpoint=self.azure_openai_endpoint,
            api_version=self.api_version,
            ad_token_provider=token_provider,
        )

    async def chat_async(self, prompt: str) -> str:
        """Override in child class."""
        raise NotImplementedError("chat_async should be implemented in subclass.")