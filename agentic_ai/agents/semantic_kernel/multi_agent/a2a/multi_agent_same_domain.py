import logging
from agents.base_agent import BaseAgent
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Agent(BaseAgent):
    def __init__(self, state_store, session_id) -> None:
        super().__init__(state_store, session_id)
        self.logistic_mcp_server_uri = os.getenv("LOGISTIC_MCP_SERVER_URI") 
        self._agent = None
        self._initialized = False

    async def _setup_agents(self) -> None:
        """Initialize the assistant and tools only once."""
        if self._initialized:
            return

        # Set up the SSE plugin for the MCP service.
        contoso_plugin = MCPSsePlugin(
            name="ContosoMCP",
            description="Contoso MCP Plugin",
            url=self.mcp_server_uri,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        logistic_plugin = MCPSsePlugin(
            name="LogisticMCP",
            description="Logistic MCP Plugin",
            url=self.mcp_server_uri,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        await logistic_plugin.connect()
        # Open the SSE connection so tools/prompts are loaded
        await contoso_plugin.connect()
        logistic_agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="logistic_agent",
            instructions="Schedule pick-up for a product return. First, when you receive a request to schedule pick up from an address, check your availability options and return the available slots. "
            "If the customer accepts a slot, schedule the pick-up and return the confirmation. ",
            plugins=[logistic_plugin]
        )

        # Define compete agents and use them to create the main agent.
        self.customer_service_agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="customer_service_agent",
            instructions="You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
            "When customer ask for a product return, first check if the product is eligible for return, that is if the order has been delivered and check with customer if the condition of the product is acceptable and the return is within 30 days of delivery. "  
            "If the product is eligible for return, ask customer for their address, their prefered timeframe and forward all information to the logistic agent to schedule a pick-up. Ask logistic agent for 3 options within the next week. " ,
            plugins=[contoso_plugin, logistic_agent]
        )
        # Create a thread to hold the conversation.
        self._thread: ChatHistoryAgentThread | None = None
        # Re‑create the thread from persisted state (if any)
        if self.state and isinstance(self.state, dict) and "thread" in self.state:
            try:
                self._thread = self.state["thread"]
                logger.info("Restored thread from SESSION_STORE")
            except Exception as e:
                logger.warning(f"Could not restore thread: {e}")

        self._initialized = True

    async def chat_async(self, prompt: str) -> str:
        # Ensure agent/tools are ready and process the prompt.
        await self._setup_agents()

        response = await self.customer_service_agent.get_response(messages=prompt, thread=self._thread)
        response_content = str(response.content)

        self._thread = response.thread
        if self._thread:
            self._setstate({"thread": self._thread})

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response_content},
        ]
        self.append_to_chat_history(messages)

        return response_content
