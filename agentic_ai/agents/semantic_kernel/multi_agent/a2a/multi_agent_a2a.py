"""  
Multi-agent Customer-Service assistant  
  
• Keeps Contoso MCP tools as before  
• Talks to the remote Logistics agent **via its A2A server**  
  through a single stateful “chat” tool.  
• Maintains taskId / contextId automatically inside self.state  
"""  
from __future__ import annotations  
  
import asyncio  
import json  
import logging  
import os  
from uuid import uuid4  
from typing import Any, Dict, Optional  
  
import httpx  
from a2a.client import A2ACardResolver, A2AClient  
from a2a.types import MessageSendParams, SendMessageRequest  
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread  
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion  
from semantic_kernel.connectors.mcp import MCPSsePlugin  
from semantic_kernel.functions import kernel_function  
  
from agents.base_agent import BaseAgent  
  
# ─────────────────────────  Logging  ──────────────────────────  
logging.basicConfig(  
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"  
)  
logger = logging.getLogger(__name__)  
  
# ══════════════════  STATEFUL LOGISTICS A2A PLUGIN  ══════════════════  
class LogisticsA2AChatPlugin:  
    """  
    Acts as a proxy to the remote Logistics agent (A2A server).  
    Accepts *free-text* requests and maintains contextId / taskId to keep  
    the conversation thread alive on the server.  
    """  
  
    def __init__(self, base_url: str) -> None:  
        self.base_url = base_url.rstrip("/")  
        self._httpx: Optional[httpx.AsyncClient] = None  
        self._client: Optional[A2AClient] = None  
  
        # A2A conversation identifiers (persisted by the outer Agent)  
        self.context_id: Optional[str] = None  
        self.task_id: Optional[str] = None  
  
    # --------  connection bootstrap  ----------------------------------  
    async def _ensure_client(self) -> None:  
        if self._client:  
            return  
        self._httpx = httpx.AsyncClient(timeout=60)  
        resolver = A2ACardResolver(self._httpx, base_url=self.base_url)  
        card = await resolver.get_agent_card()  
        self._client = A2AClient(httpx_client=self._httpx, agent_card=card)  
        logger.info("LogisticsA2AChatPlugin connected → %s", self.base_url)  
  
    # --------  the single exposed tool  -------------------------------  
    @kernel_function(  
        name="logistics_agent",  
        description=(  
        "Logistics AI agent responsible for arranging product-return "  
        "pick-ups."  
        "Supported request types:\n"  
        "  • availability_request\n"  
        "  • schedule_pickup\n"  
        "  • cancel_request\n"       
         ),  
    )  
    async def chat(self, message: str) -> str:  
        """  
        Free-text bridge to Logistics.  Keeps the server-side  
        conversation alive by sending previously returned contextId /  
        taskId whenever available.  
        """  
        await self._ensure_client()  
  
        msg_dict: Dict[str, Any] = {  
            "role": "user",  
            "parts": [{"kind": "text", "text": message}],  
            "messageId": uuid4().hex,  
        }  
        if self.context_id and self.task_id:  
            msg_dict["contextId"] = self.context_id  
            msg_dict["taskId"] = self.task_id  
  
        request = SendMessageRequest(  
            id=str(uuid4()), params=MessageSendParams(message=msg_dict)  
        )  
        # ---------- call remote A2A server --------------------------  
        response = await self._client.send_message(request)  
  
        # Parse text content + new task/context IDs  
        payload = response.model_dump(mode="python", exclude_none=True)["result"]  
        self.task_id = payload.get("taskId") or self.task_id  
        self.context_id = payload.get("contextId") or self.context_id  
        text = payload["parts"][0]["text"]  
  
        return text  
  
  
# ═════════════════════════  MAIN AGENT  ══════════════════════════════  
class Agent(BaseAgent):  
    def __init__(self, state_store, session_id) -> None:  
        super().__init__(state_store, session_id)  
  
        # URLs / env ---------------------------------------------------  
        self.logistics_a2a_url = os.getenv("LOGISTICS_A2A_URL", "http://localhost:9100")  
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI")  
  
        # runtime members ---------------------------------------------  
        self._initialized = False  
        self._thread: ChatHistoryAgentThread | None = None  
        self._logistics_plugin: Optional[LogisticsA2AChatPlugin] = None  
  
    # ----------------------------------------------------------------  
    async def _setup_agents(self) -> None:  
        if self._initialized:  
            return  
  
        # --- Contoso domain tools (unchanged) ------------------------  
        contoso_plugin = MCPSsePlugin(  
            name="ContosoMCP",  
            description="Contoso MCP Plugin",  
            url=self.mcp_server_uri,  
            headers={"Content-Type": "application/json"},  
            timeout=30,  
        )  
        await contoso_plugin.connect()  
  
        # --- Logistics chat plugin -----------------------------------  
        self._logistics_plugin = LogisticsA2AChatPlugin(self.logistics_a2a_url)  
  
        # restore persisted A2A ids (if any)  
        if isinstance(self.state, dict):  
            self._logistics_plugin.context_id = self.state.get("logistics_context_id")  
            self._logistics_plugin.task_id = self.state.get("logistics_task_id")  
  
        # ensure the plugin is ready (creates A2A client)  
        await self._logistics_plugin._ensure_client()  
  
        # --- Customer-Service LLM agent ------------------------------  
        self.customer_service_agent = ChatCompletionAgent(  
            service=AzureChatCompletion(),  
            name="customer_service_agent",  
            instructions=( "You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
            "When customer ask for a product return, first check if the product is eligible for return, that is if the order has been delivered and check with customer if the condition of the product is acceptable and the return is within 30 days of delivery. "  
            "If the product is eligible for return, ask customer for their address, their prefered timeframe and forward all information to the logistic agent to schedule a pick-up. Ask logistic agent for 3 options within the next week. " 
            ),  
            plugins=[  
                contoso_plugin,  
                self._logistics_plugin,  
            ],  
        )  
  
        # restore chat thread (if any)  
        if isinstance(self.state, dict) and "thread" in self.state:  
            try:  
                self._thread = self.state["thread"]  
                logger.info("Restored thread from SESSION_STORE")  
            except Exception as e:  # pragma: no cover  
                logger.warning("Could not restore thread: %s", e)  
  
        self._initialized = True  
  
    # ----------------------------------------------------------------  
    async def chat_async(self, prompt: str) -> str:  
        await self._setup_agents()  
        logging.info("prompt: %s", prompt)
  
        response = await self.customer_service_agent.get_response(  
            messages=prompt, thread=self._thread  
        )  
        response_content = str(response.content)  
        logging.info("response: %s", response_content)
  
        # ---------- persist state ------------------------------------  
        self._thread = response.thread  
        persist: Dict[str, Any] = {"thread": self._thread}  
        if self._logistics_plugin:  
            persist["logistics_context_id"] = self._logistics_plugin.context_id  
            persist["logistics_task_id"] = self._logistics_plugin.task_id  
        self._setstate(persist)  
  
        # ---------- chat history for UI / analytics ------------------  
        self.append_to_chat_history(  
            [  
                {"role": "user", "content": prompt},  
                {"role": "assistant", "content": response_content},  
            ]  
        )  
        return response_content  