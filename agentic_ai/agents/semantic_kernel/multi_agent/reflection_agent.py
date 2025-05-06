import logging
from agents.base_agent import BaseAgent
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Agent(BaseAgent):
    def __init__(self, state_store, session_id) -> None:
        super().__init__(state_store, session_id)
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

        # Open the SSE connection so tools/prompts are loaded
        await contoso_plugin.connect()

        # Define compete agents and use them to create the main agent.
        primary_agent = ChatCompletionAgent(
            service=AzureChatCompletion(deployment_name=self.azure_deployment),
            name="PrimaryAgent",
            instructions="You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
            "Review the tools available to you and use them as needed. You can also ask clarifying questions if "  
            "the user is not clear." ,
            plugins=[contoso_plugin]
        )
        critic_agent = ChatCompletionAgent(
            service=AzureChatCompletion(deployment_name=self.azure_deployment),
            name="CriticAgent",
            instructions="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
            plugins=[contoso_plugin]
        )
        self._agent = ChatCompletionAgent(
            service=AzureChatCompletion(deployment_name=self.azure_deployment),
            name="ChatBot",
            instructions=("You coordinate between PrimaryAgent and CriticAgent. "
                "First, get the response from PrimaryAgent, then ask CriticAgent to review it. "
                "Finally, present the improved response to the user if needed."
            ),
            plugins=[primary_agent, critic_agent]
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

        response = await self._agent.get_response(messages=prompt, thread=self._thread)
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
