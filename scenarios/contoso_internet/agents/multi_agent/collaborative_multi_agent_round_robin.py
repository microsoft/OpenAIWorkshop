import logging  
from typing import Any, List  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import RoundRobinGroupChat  # keeps implementation simple & familiar  
from autogen_agentchat.conditions import TextMessageTermination  
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  
  
from agents.base_agent import BaseAgent  
  
  
class Agent(BaseAgent):  
    """  
    Collaborative multi‑agent system composed of:  
        • Analysis & Planning Agent (orchestrator)  
        • CRM & Billing Agent  
        • Product & Promotions Agent  
        • Security & Authentication Agent  
  
    Each specialist has access to the central Knowledge Base through the  
    mcp_server_tools tool‑suite.  The Analysis & Planning Agent orchestrates  
    the conversation and produces the final answer.  
  
    Conversations finish when the Analysis & Planning Agent sends its  
    synthesis (TextMessageTermination("analysis_planning")).  
    """  
  
    def __init__(self, state_store: dict, session_id: str) -> None:  
        super().__init__(state_store, session_id)  
        self.team_agent: Any = None  
        self._initialized: bool = False  
  
    # --------------------------------------------------------------------- #  
    #                         TEAM INITIALISATION                           #  
    # --------------------------------------------------------------------- #  
    async def _setup_team_agent(self) -> None:  
        """Create/restore the collaborative team once per session."""  
        if self._initialized:  
            return  
  
        try:  
            # 1. -----------------  Shared Tooling (Knowledge Base access)  -----------------  
            server_params = SseServerParams(  
                url=self.mcp_server_uri,  
                headers={"Content-Type": "application/json"},  
                timeout=30,  
            )  
            tools = await mcp_server_tools(server_params)  
  
            # 2. -----------------  Shared Model Client -----------------  
            model_client = AzureOpenAIChatCompletionClient(  
                api_key=self.azure_openai_key,  
                azure_endpoint=self.azure_openai_endpoint,  
                api_version=self.api_version,  
                azure_deployment=self.azure_deployment,  
                model=self.openai_model_name,  
            )  
  
            # 3. -----------------  Agent Definitions -----------------  
            analysis_planning_agent = AssistantAgent(  
                name="analysis_planning",  
                model_client=model_client,  
                tools=tools,  
                system_message=(  
                    "You are the Analysis & Planning Agent – the orchestrator. "  
                    "Your responsibilities:\n"  
                    "1) Parse the customer's abstract request.\n"  
                    "2) Break it down into clear subtasks and delegate them to the "  
                    "domain specialists (crm_billing, product_promotions, "  
                    "security_authentication).\n"  
                    "3) Integrate the specialists' outputs into ONE comprehensive, "  
                    "coherent answer for the customer.\n"  
                    "4) When satisfied, respond to the customer with the final answer "  
                    "prefixed by: FINAL ANSWER:\n\n"  
                    "If you still need information, continue the dialogue with the "  
                    "specialists; otherwise finish with the final answer."  
                ),  
            )  
  
            crm_billing_agent = AssistantAgent(  
                name="crm_billing",  
                model_client=model_client,  
                tools=tools,  
                system_message=(  
                    "You are the CRM & Billing Agent.\n"  
                    "- Query structured CRM / billing systems for account, subscription, "  
                    "invoice, and payment information as needed.\n"  
                    "- Check *Knowledge Base* articles on billing policies, payment "  
                    "processing, refund rules, etc., to ensure responses are accurate "  
                    "and policy‑compliant.\n"  
                    "- Reply with concise, structured information and flag any policy "  
                    "concerns you detect."  
                ),  
            )  
  
            product_promotions_agent = AssistantAgent(  
                name="product_promotions",  
                model_client=model_client,  
                tools=tools,  
                system_message=(  
                    "You are the Product & Promotions Agent.\n"  
                    "- Retrieve promotional offers, product availability, eligibility "  
                    "criteria, and discount information from structured sources.\n"  
                    "- Augment answers with *Knowledge Base* FAQs, terms & conditions, "  
                    "and best practices.\n"  
                    "- Provide factual, up‑to‑date product/promo details."  
                ),  
            )  
  
            security_authentication_agent = AssistantAgent(  
                name="security_authentication",  
                model_client=model_client,  
                tools=tools,  
                system_message=(  
                    "You are the Security & Authentication Agent.\n"  
                    "- Investigate authentication logs, account lockouts, and security "  
                    "incidents in structured security databases.\n"  
                    "- Always cross‑reference *Knowledge Base* security policies and "  
                    "lockout troubleshooting guides.\n"  
                    "- Return clear risk assessments and recommended remediation steps."  
                ),  
            )  
  
            # 4. -----------------  Assemble Team -----------------  
            # Round‑robin is an easy default: the orchestrator is placed last so that  
            # after specialists have spoken it can collect & finish.  The chat  
            # stops whenever the orchestrator speaks (regardless of content) because  
            # TextMessageTermination is keyed on the agent name.  
            participants: List[AssistantAgent] = [  
                crm_billing_agent,  
                product_promotions_agent,  
                security_authentication_agent,  
                analysis_planning_agent,      # orchestrator always concludes a cycle  
            ]  
  
            termination_condition = TextMessageTermination("analysis_planning")  
  
            self.team_agent = RoundRobinGroupChat(  
                participants=participants,  
                termination_condition=termination_condition,  
            )  
  
            # 5. -----------------  Restore persisted state (if any) -----------------  
            if self.state:  
                await self.team_agent.load_state(self.state)  
  
            self._initialized = True  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainAgent] Initialisation failure: {exc}")  
            raise  # re‑raise so caller is aware something went wrong  
  
    # --------------------------------------------------------------------- #  
    #                              CHAT ENTRY                               #  
    # --------------------------------------------------------------------- #  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Executes the collaborative multi‑agent chat for a given user prompt.  
  
        Returns  
        -------  
        str  
            The final, synthesised reply produced by the Analysis & Planning Agent.  
        """  
        await self._setup_team_agent()  
  
        try:  
            response = await self.team_agent.run(  
                task=prompt,  
                cancellation_token=CancellationToken(),  
            )  
  
            assistant_response: str = response.messages[-1].content  
  
            # Persist interaction in chat history so UI / analytics can render it.  
            self.append_to_chat_history(  
                [  
                    {"role": "user", "content": prompt},  
                    {"role": "assistant", "content": assistant_response},  
                ]  
            )  
  
            # Persist internal Agent‑Chat state for future turns / resumptions.  
            new_state = await self.team_agent.save_state()  
            self._setstate(new_state)  
  
            return assistant_response  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainAgent] chat_async error: {exc}")  
            return (  
                "Apologies, an unexpected error occurred while processing your "  
                "request.  Please try again later."  
            )  