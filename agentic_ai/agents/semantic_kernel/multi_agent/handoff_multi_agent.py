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

        service = AzureChatCompletion(
            api_key=self.azure_openai_key,
            endpoint=self.azure_openai_endpoint,
            api_version=self.api_version,
            deployment_name=self.azure_deployment,
        )

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
        crm_billing = ChatCompletionAgent(
            service=service,
            name="crm_billing",
            instructions="You are the CRM & Billing Agent.\n"
            "- Query structured CRM / billing systems for account, subscription, "
            "invoice, and payment information as needed.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* articles on billing policies, payment "
            "processing, refund rules, etc., to ensure responses are accurate "
            "and policy‑compliant.\n"
            "- Reply with concise, structured information and flag any policy "
            "concerns you detect.\n"
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            plugins=[contoso_plugin],
        )

        product_promotions = ChatCompletionAgent(
            service=service,
            name="product_promotions",
            instructions="You are the Product & Promotions Agent.\n"
            "- Retrieve promotional offers, product availability, eligibility "
            "criteria, and discount information from structured sources.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* FAQs, terms & conditions, "
            "and best practices.\n"
            "- Provide factual, up‑to‑date product/promo details."
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            plugins=[contoso_plugin],
        )

        security_authentication = ChatCompletionAgent(
            service=service,
            name="security_authentication",
            instructions="You are the Security & Authentication Agent.\n"
            "- Investigate authentication logs, account lockouts, and security "
            "incidents in structured security databases.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* security policies and "
            "lockout troubleshooting guides.\n"
            "- Return clear risk assessments and recommended remediation steps."
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            plugins=[contoso_plugin],
        )

        self._agent = ChatCompletionAgent(
            service=service,
            name="triage_agent",
            instructions=(
                 "Handoff to the appropriate agent based on the language of the request."
                "if you need clarification or info is not complete ask follow-up Qs"
                "Like if customer asks questions without providing any identifying info such as customer ID, ask for it"
            ),
            plugins=[crm_billing, product_promotions, security_authentication],
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
