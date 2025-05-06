import os  
import logging  
from typing import Any, Dict, List, Optional  
from dotenv import load_dotenv  
  
load_dotenv()  # Load environment variables from .env file if needed  
  
class BaseAgent:  
    """  
    Base class for all agents.  
    Not intended to be used directly.  
    Handles environment variables, state store, and chat history.  
    """  
  
    def __init__(self, state_store: Dict[str, Any], session_id: str) -> None:  
        self.azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")  
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")  
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")  
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI")  
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME")  
  
        self.session_id = session_id  
        self.state_store = state_store  
  
        self.chat_history: List[Dict[str, str]] = self.state_store.get(f"{session_id}_chat_history", [])  
        self.state: Optional[Any] = self.state_store.get(session_id, None) 
        logging.debug(f"Chat history for session {session_id}: {self.chat_history}")  
  
    def _setstate(self, state: Any) -> None:  
        self.state_store[self.session_id] = state  
  
    def append_to_chat_history(self, messages: List[Dict[str, str]]) -> None:  
        self.chat_history.extend(messages)  
        self.state_store[f"{self.session_id}_chat_history"] = self.chat_history  
  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Override in child class!  
        """  
        raise NotImplementedError("chat_async should be implemented in subclass.")  