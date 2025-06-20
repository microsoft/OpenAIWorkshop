import asyncio
import logging
from typing import List, Optional

from agents.base_agent import BaseAgent
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelArguments, KernelFunctionFromPrompt

from semantic_kernel import Kernel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Agent(BaseAgent):
    """
    Multi‑domain, SK‑based collaborative agent.

    Participants
    ------------
    • analysis_planning        – orchestrator, produces FINAL ANSWER
    • crm_billing              – billing specialist
    • product_promotions       – promotions / offers specialist
    • security_authentication  – security specialist
    """

    def __new__(cls, state_store: dict, session_id: str):
        # Return the existing instance if it exists in the session store.
        if session_id in state_store:
            return state_store[session_id]
        instance = super().__new__(cls)
        state_store[session_id] = instance
        return instance

    def __init__(self, state_store: dict, session_id: str) -> None:
        # Prevent re‑initialization if the instance was already constructed.
        if hasattr(self, "_constructed"):
            return
        self._constructed = True
        super().__init__(state_store, session_id)
        self._chat: AgentGroupChat

    async def _setup_team(self) -> None:
        if getattr(self, "_initialized", False):
            return

        # 1. ---------- "System" Kernel + Service (Azure OpenAI) ---------------
        system_kernel = Kernel()
        system_kernel.add_service(
            service=AzureChatCompletion(
                api_key=self.azure_openai_key,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
                deployment_name=self.azure_deployment,
            )
        )

        # 2. ---------- Shared MCP SSE plugin ----------------------------
        self.contoso_plugin = MCPSsePlugin(
            name="ContosoMCP",
            description="Contoso MCP Plugin",
            url=self.mcp_server_uri,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        await self.contoso_plugin.connect()

        # 3. Helper: build a fresh kernel for each agent + settings helper
        specialist_kernel = Kernel()
        specialist_kernel.add_service(
            service=AzureChatCompletion(
                api_key=self.azure_openai_key,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
                deployment_name=self.azure_deployment,
            )
        )
        # Register the shared plugin so specialists can call its functions
        specialist_kernel.add_plugin(self.contoso_plugin, plugin_name="ContosoMCP")

        # 3. ---------- Helper to create a participant -------------------
        def make_agent(
            name: str,
            instructions: str,
            kernel: Kernel,
            included_tools: Optional[List[str]] = [],
        ) -> ChatCompletionAgent:
            settings = kernel.get_prompt_execution_settings_from_service_id("default")
            settings.function_choice_behavior = FunctionChoiceBehavior.Auto(
                filters={"included_functions": included_tools}
            )

            return ChatCompletionAgent(
                kernel=kernel,
                name=name,
                instructions=instructions,
                arguments=KernelArguments(settings=settings),
            )

        # 4. ---------- Participants ------------------------------------
        analysis_planning = make_agent(
            "analysis_planning",
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
            "- Never include ‘FINAL ANSWER’ when talking to a specialist.\n",
            kernel=system_kernel,
        )

        crm_billing = make_agent(
            "crm_billing",
            "You are the CRM & Billing Agent.\n"
            "- Query structured CRM / billing systems for account, subscription, "
            "invoice, and payment information as needed.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* articles on billing policies, payment "
            "processing, refund rules, etc., to ensure responses are accurate "
            "and policy‑compliant.\n"
            "- Reply with concise, structured information and flag any policy "
            "concerns you detect.\n"
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            kernel=specialist_kernel,
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
        )

        product_promotions = make_agent(
            "product_promotions",
            "You are the Product & Promotions Agent.\n"
            "- Retrieve promotional offers, product availability, eligibility "
            "criteria, and discount information from structured sources.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* FAQs, terms & conditions, "
            "and best practices.\n"
            "- Provide factual, up‑to‑date product/promo details."
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            kernel=specialist_kernel,
            included_tools=[
                "ContosoMCP-get_all_customers",
                "ContosoMCP-get_customer_detail",
                "ContosoMCP-get_promotions",
                "ContosoMCP-get_eligible_promotions",
                "ContosoMCP-search_knowledge_base",
                "ContosoMCP-get_products",
                "ContosoMCP-get_product_detail",
            ],
        )

        security_authentication = make_agent(
            "security_authentication",
            "You are the Security & Authentication Agent.\n"
            "- Investigate authentication logs, account lockouts, and security "
            "incidents in structured security databases.\n"
            "- For each response you **MUST** cross‑reference relevant *Knowledge Base* security policies and "
            "lockout troubleshooting guides.\n"
            "- Return clear risk assessments and recommended remediation steps."
            "Only respond with data you retrieve using your tools.\n"
            "DO NOT respond to anything out of your domain.",
            kernel=specialist_kernel,
            included_tools=[
                "ContosoMCP-get_all_customers",
                "ContosoMCP-get_customer_detail",
                "ContosoMCP-get_security_logs",
                "ContosoMCP-search_knowledge_base",
                "ContosoMCP-unlock_account",
            ],
        )

        participants: List[ChatCompletionAgent] = [
            crm_billing,
            product_promotions,
            security_authentication,
            analysis_planning,  # orchestrator closes a cycle
        ]

        participant_names = [p.name for p in participants]

        # 5. ---------- Selection & Termination strategies ---------------
        selection_prompt = KernelFunctionFromPrompt(
            function_name="selection",
            prompt=f"""
                Decide which participant must speak next by inspecting the text
                of the most recent message.

                ROUTING RULES
                1. If the last message begins (ignoring leading whitespace and
                   case) with one of the specialist prefixes below, send the turn
                   to that specialist:
                       "crm_billing:"             -> crm_billing
                       "product_promotions:"      -> product_promotions
                       "security_authentication:" -> security_authentication

                2. Otherwise (e.g. the last message came from a specialist or the
                   user) send the turn to analysis_planning.

                3. Never allow the same participant to speak twice in a row.

                Respond with the participant name only – no extra words.

                VALID PARTICIPANTS:
                {chr(10).join('- ' + n for n in participant_names)}

                LAST MESSAGE:
                {{{{$lastmessage}}}}
                """,
        )

        termination_keyword = "final answer:"
        termination_prompt = KernelFunctionFromPrompt(
            function_name="termination",
            prompt=f"""
                If RESPONSE starts with "{termination_keyword}" (case‑insensitive),
                respond with YES, otherwise NO.

                RESPONSE:
                {{{{$lastmessage}}}}
                """,
        )

        history_reducer = ChatHistoryTruncationReducer(target_count=8)

        self._chat = AgentGroupChat(
            agents=participants,
            selection_strategy=KernelFunctionSelectionStrategy(
                initial_agent=analysis_planning,
                function=selection_prompt,
                kernel=system_kernel,
                result_parser=lambda r: str(r.value[0]).strip(),
                history_variable_name="lastmessage",
                history_reducer=history_reducer,
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                agents=[analysis_planning],
                function=termination_prompt,
                kernel=system_kernel,
                result_parser=lambda r: str(r.value[0]).lower().startswith("yes"),
                history_variable_name="lastmessage",
                maximum_iterations=15,
                history_reducer=history_reducer,
            ),
        )

        self._initialized = True

    # ------------------------------------------------------------------ #
    #                              CHAT API                               #
    # ------------------------------------------------------------------ #
    async def chat_async(self, prompt: str) -> str:
        """Runs the multi‑agent collaboration and returns the orchestrator's FINAL ANSWER."""
        await self._setup_team()

        if not self._chat:
            return "Multi‑agent system not initialised."

        if self._chat.is_complete:
            self._chat.is_complete = False

        # Add the user message to the conversation
        await self._chat.add_chat_message(message=prompt)

        final_answer: str = ""

        try:
            async for response in self._chat.invoke():
                if response and response.name:
                    logger.info(f"[{response.name}] {response.content}")
                    # capture orchestrator final answer
                    if response.name == "analysis_planning" and str(
                        response.content
                    ).lower().startswith("final answer:"):
                        # Remove the prefix (case‑insensitive)
                        final_answer = str(response.content).split(":", 1)[1].lstrip()

        except Exception as exc:
            logger.error(f"[SK MultiAgent] chat_async error: {exc}")
            return (
                "Sorry, something went wrong while processing your request. "
                "Please try again later."
            )

        # Fallback if orchestrator did not produce final answer
        if not final_answer:
            final_answer = "Sorry, the team could not reach a conclusion within the allotted turns."

        # Append to chat history visible to the UI
        self.append_to_chat_history(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_answer},
            ]
        )

        return final_answer


# --------------------------- Manual test helper --------------------------- #
# if __name__ == "__main__":

#     async def _demo() -> None:
#         dummy_state: dict = {}
#         agent = Agent(dummy_state, session_id="demo")
#         user_question = "My customer id is 101, why is my internet bill so high?"
#         answer = await agent.chat_async(user_question)
#         print("\n>>> Assistant reply:\n", answer)
#         try:
#             await agent.contoso_plugin.close()
#         except Exception as exc:
#             logger.warning(f"SSE plugin close failed: {exc}")

#     asyncio.run(_demo())
