"""
Step-by-step debugging and serialization workflow for multi-agent orchestration:

1. Run the manual test at the bottom of this file (or import and call Agent.chat_async) with a sample user question.
2. Observe the console/log output for each agent response. Each message will print:
   - The agent name
   - The message content
   - The type of the message content
3. If a serialization error occurs, check the logs for the last message type/value. If it is not a string or JSON-serializable, the log will show the problematic value and type.
4. If you see a non-serializable type (e.g., a custom object, coroutine, or generator), update the agent or orchestration logic to convert it to a string or dict before returning.
5. Repeat until all agent responses are serializable and the orchestration completes without error.
6. If you need to debug a specific agent, add more print/log statements in its respond method or tool call.
7. Once stable, remove or reduce debug logging as needed.
"""

import asyncio
import logging
import json
from typing import Optional

from agents.base_agent import BaseAgent
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, GroupChatOrchestration, RoundRobinGroupChatManager
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
from semantic_kernel.functions import KernelArguments

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Agent(BaseAgent):
    def __new__(cls, state_store: dict, session_id: str):
        if session_id in state_store:
            return state_store[session_id]
        instance = super().__new__(cls)
        state_store[session_id] = instance
        return instance

    def __init__(self, state_store: dict, session_id: str) -> None:
        if hasattr(self, "_constructed"):
            return
        self._constructed = True
        super().__init__(state_store, session_id)
        self._orchestration: Optional[GroupChatOrchestration] = None
        self._group_chat_runtime: Optional[InProcessRuntime] = None

    async def _setup_team(self) -> None:
        if getattr(self, "_initialized", False):
            return

        # Setup Azure OpenAI service
        service = AzureChatCompletion(
            api_key=self.azure_openai_key,
            endpoint=self.azure_openai_endpoint,
            api_version=self.api_version,
            deployment_name=self.azure_deployment,
        )

        # Setup MCP SSE Plugin (backend connection)
        self.contoso_plugin = MCPSsePlugin(
            name="ContosoMCP",
            description="Contoso MCP Plugin",
            url=self.mcp_server_uri,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        await self.contoso_plugin.connect()

        # Setup kernel with services and plugins
        specialist_kernel = Kernel()
        specialist_kernel.add_service(service)
        specialist_kernel.add_plugin(self.contoso_plugin, plugin_name="ContosoMCP")

        def make_agent(name, description, instructions, included_tools=[]):
            # Debug: Log agent creation details
            logger.info(f"[DEBUG] Creating agent: {name}\nDescription: {description}\nIncluded tools: {included_tools}")
            
            settings = specialist_kernel.get_prompt_execution_settings_from_service_id("default")
            function_choice_behavior = FunctionChoiceBehavior.Auto(
                filters={"included_functions": included_tools} if included_tools else None
            )
            
            agent = ChatCompletionAgent(
                name=name,
                description=description,
                instructions=instructions,
                service=service,
                function_choice_behavior=function_choice_behavior,
                kernel=specialist_kernel,
            )
            
            return agent

        participants = [
            make_agent(
                name="crm_billing",
                description="CRM & Billing Agent",
                instructions=(
                    "You are the CRM & Billing Agent.\n"
                    "- Query structured CRM / billing systems for account, subscription, "
                    "invoice, and payment information as needed.\n"
                    "- For each response you **MUST** cross‑reference relevant *Knowledge Base* articles on billing policies, payment "
                    "processing, refund rules, etc., to ensure responses are accurate "
                    "and policy‑compliant.\n"
                    "- Reply with concise, structured information and flag any policy "
                    "concerns you detect.\n"
                    "Only respond with data you retrieve using your tools.\n"
                    "DO NOT respond to anything out of your domain."
                ),
                included_tools=[
                    "ContosoMCP-get_all_customers",
                    "ContosoMCP-get_customer_detail",
                    "ContosoMCP-get_subscription_detail",
                    "ContosoMCP-get_invoice_payments",
                    "ContosoMCP-pay_invoice",
                    "ContosoMCP-get_data_usage",
                    "ContosoMCP-search_knowledge_base",
                    "ContosoMCP-get_customer_orders",
                    "ContosoMCP-update_subscription",
                    "ContosoMCP-get_billing_summary",
                ],
            ),
            make_agent(
                name="product_promotions",
                description="Product & Promo Agent",
                instructions=(
                    "You are the Product & Promotions Agent.\n"
                    "- Retrieve promotional offers, product availability, eligibility "
                    "criteria, and discount information from structured sources.\n"
                    "- For each response you **MUST** cross‑reference relevant *Knowledge Base* FAQs, terms & conditions, "
                    "and best practices.\n"
                    "- Provide factual, up‑to‑date product/promo details."
                    "Only respond with data you retrieve using your tools.\n"
                    "DO NOT respond to anything out of your domain."
                ),
                included_tools=[
                    "ContosoMCP-get_all_customers",
                    "ContosoMCP-get_customer_detail",
                    "ContosoMCP-get_promotions",
                    "ContosoMCP-get_eligible_promotions",
                    "ContosoMCP-search_knowledge_base",
                    "ContosoMCP-get_products",
                    "ContosoMCP-get_product_detail",
                ],
            ),
            make_agent(
                name="security_authentication",
                description="Security & Authentication Agent",
                instructions=(
                    "You are the Security & Authentication Agent.\n"
                    "- Investigate authentication logs, account lockouts, and security "
                    "incidents in structured security databases.\n"
                    "- For each response you **MUST** cross‑reference relevant *Knowledge Base* security policies and "
                    "lockout troubleshooting guides.\n"
                    "- Return clear risk assessments and recommended remediation steps."
                    "Only respond with data you retrieve using your tools.\n"
                    "DO NOT respond to anything out of your domain."
                ),
                included_tools=[
                    "ContosoMCP-get_all_customers",
                    "ContosoMCP-get_customer_detail",
                    "ContosoMCP-get_security_logs",
                    "ContosoMCP-search_knowledge_base",
                    "ContosoMCP-unlock_account",
                ],
            ),
            make_agent(
                name="analysis_planning",
                description="Analysis & Planning Agent",
                instructions=(
                    "You are the Analysis & Planning Agent (the planner/orchestrator).\n"
                    "\n"
                    "1. Decide if the user’s request can be satisfied directly:\n"
                    "   - If YES (e.g. greetings, very simple Q&A), answer immediately using the prefix:\n"
                    "     FINAL ANSWER: <your reply>\n"
                    "\n"
                    "2. Otherwise you MUST delegate atomic sub‑tasks one‑by‑one to specialists.\n"
                    "   - Output format WHEN DELEGATING (strict):\n"
                    "       <specialist_name>: <task>\n"
                    "     – No other text, no quotation marks, no ‘FINAL ANSWER’.\n"
                    "   - Delegate only one sub‑task per turn, then wait for the specialist’s reply.\n"
                    "\n"
                    "3. After all required information is gathered, compose ONE comprehensive response and\n"
                    "   send it to the user prefixed with:\n"
                    "   FINAL ANSWER: <your synthesized reply>\n"
                    "\n"
                    "4. If you need clarification from the user, ask it immediately and prefix with\n"
                    "   FINAL ANSWER: <your question>\n"
                    "\n"
                    "Pay close attention to user query and identify keywords that you can find in agent definition/instruction to correctly delegate the task.\n"
                    "Specialist directory – choose the SINGLE best match for each sub‑task:\n"
                    "- crm_billing – Accesses CRM & billing systems for account, subscription, invoice,\n"
                    "  payment status, refunds and policy compliance questions.\n"
                    "- product_promotions – Provides product catalogue details, current promotions,\n"
                    "  discount eligibility rules and T&Cs from structured sources & FAQs.\n"
                    "- security_authentication – Investigates authentication logs, account lock‑outs,\n"
                    "  security incidents; references security KBs and recommends remediation steps.\n"
                    "\n"
                    "STRICT RULES:\n"
                    "- Do not emit planning commentary or bullet lists to the user.\n"
                    "- Only ‘FINAL ANSWER’ messages or specialist delegations are allowed.\n"
                    "- After all agents discuss, make sure you respond only relevant information asked as per user request.\n"
                    "- It's possible in taking multiple turns you got different answers, but the most appropraite response was in one of the earlier rounds, so look at keywords in questions and map the response to closest keyword matching\n"
                    "- Never include ‘FINAL ANSWER’ when talking to a specialist.\n"
                ),
            ),
        ]

        # Setup orchestration & runtime
        self._orchestration = GroupChatOrchestration(
            members=participants,
            manager=RoundRobinGroupChatManager(
                max_rounds=1,
                allow_repeat_speaker=False,
                initial_speaker="analysis_planning",
                completion_criteria=lambda message: str(message.content).lower().startswith("final answer:")
            )
        )
        self._group_chat_runtime = InProcessRuntime()
        self._group_chat_runtime.start()

        self._initialized = True

    def to_serializable(self, obj):
        """Recursively convert an object to something JSON-serializable."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {k: self.to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self.to_serializable(v) for v in obj]
        # Try to extract common content/text attributes
        for attr in ("text", "content", "value", "data"):
            if hasattr(obj, attr):
                return self.to_serializable(getattr(obj, attr))
        # Fallback: string representation
        return str(obj)

    async def chat_async(self, prompt: str) -> str:
        await self._setup_team()

        if not self._orchestration or not self._group_chat_runtime:
            return "Multi-agent system not initialized."

        try:
            orchestration_result = await self._orchestration.invoke(
                task=prompt,
                runtime=self._group_chat_runtime,
            )

            # Get the final result directly
            value = await orchestration_result.get()

            # Debug log: show the type and repr of the value and value.content
            logger.info(f"[DEBUG] orchestration_result.get() value: {repr(value)} (type: {type(value)})")
            if hasattr(value, "content"):
                logger.info(f"[DEBUG] value.content: {repr(value.content)} (type: {type(value.content)})")
                answer = self.to_serializable(value.content)
            else:
                answer = self.to_serializable(value)

        except Exception as e:
            logger.error(f"Agent error during orchestration: {e}")
            return "Sorry, something went wrong while processing your request."

        self.append_to_chat_history([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer}
        ])

        return str(answer)

# # --------------------------- Manual test helper --------------------------- #
# print("Script started")
# if __name__ == "__main__":
#     print("Main block running")
#     async def _demo() -> None:
#         print("Demo function started")
#         try:
#             dummy_state: dict = {}
#             agent = Agent(dummy_state, session_id="demo")
#             print("Agent created")
#             user_question = "why was my internet bill high for customer ID 101?"
#             print("Calling chat_async...")
#             answer = await agent.chat_async(user_question)
#             print("chat_async returned")
#             print("\n>>> Assistant reply:\n", answer)
#             try:
#                 await agent.contoso_plugin.close()
#             except Exception as exc:
#                 logger.warning(f"SSE plugin close failed: {exc}")
#         except Exception as exc:
#             print(f"Exception in _demo: {exc}")

#     asyncio.run(_demo())
