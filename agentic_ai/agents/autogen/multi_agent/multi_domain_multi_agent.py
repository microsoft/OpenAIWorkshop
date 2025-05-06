"""  
multi_domain_router_agent.py  
────────────────────────────  
  
Light‑weight multi‑domain routing team following the SWARM pattern.  
The *Coordinator* only detects the user’s domain‑specific intent and  
hands the request to exactly ONE specialist agent.    
Each specialist agent then works **directly with the user**.    
If the user’s next request is outside its scope, it hands the  
conversation back to the coordinator, which re‑routes to the next  
specialist.  The dialogue finishes when **any** agent returns its final  
answer prefixed by  `FINAL_ANSWER:`  (or after a safety max‑turn limit).  
  
All state is persisted exactly once per session through the inherited  
`BaseAgent` helpers (`_setstate`, `append_to_chat_history`, …).  
"""  
import logging  
from typing import Any, List  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination  
from autogen_agentchat.teams import Swarm  
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  
  
from agents.base_agent import BaseAgent  
  
  
# ────────────────────────────────────────────────────────────────────────────────  
#                              TERMINATION RULES  
# ────────────────────────────────────────────────────────────────────────────────  
text_termination = TextMentionTermination("FINAL_ANSWER")  
max_turns_termination = MaxMessageTermination(max_messages=25)  
termination_condition = text_termination | max_turns_termination  
  
  
class MultiDomainRouterAgent(BaseAgent):  
    """  
    Multi‑domain routing agent that spins‑up a SWARM consisting of:  
  
        • coordinator            – detects high‑level domain, performs routing  
        • crm_billing            – subscription / invoices / payments  
        • product_promotions     – product catalogue, promos, offers  
        • security_authentication– auth lockouts / security incidents  
  
    Conversation flow:  
        USER  → coordinator (detect) → specialist ↔ USER  
        when outside scope  ↙                           ↖  
                    coordinator (re‑route)   ← HANDOFF ←  
  
    The dialogue ends when *any* agent writes `FINAL_ANSWER:` followed by its  
    concluding response.  
    """  
  
    def __init__(self, state_store: dict, session_id: str) -> None:  
        super().__init__(state_store, session_id)  
        self.team_agent: Any = None  
        self._initialized = False  
  
    # ────────────────────────────────────────────────────────────────────────  
    #                         TEAM INITIALISATION  
    # ────────────────────────────────────────────────────────────────────────  
    async def _setup_team_agent(self) -> None:  
        """Create / restore the router‑swarm once per session."""  
        if self._initialized:  # already built in this session  
            return  
  
        try:  
            # 1. ───────────────  Shared Knowledge‑Base tooling  ───────────────  
            server_params = SseServerParams(  
                url=self.mcp_server_uri,  
                headers={"Content-Type": "application/json"},  
                timeout=30,  
            )  
            tools = await mcp_server_tools(server_params)  
  
            # 2. ───────────────  Shared LLM client  ───────────────────────────  
            model_client = AzureOpenAIChatCompletionClient(  
                api_key=self.azure_openai_key,  
                azure_endpoint=self.azure_openai_endpoint,  
                api_version=self.api_version,  
                azure_deployment=self.azure_deployment,  
                model=self.openai_model_name,  
            )  
  
            # 3. ───────────────  Agent definitions  ───────────────────────────  
            coordinator = AssistantAgent(  
                name="coordinator",  
                model_client=model_client,  
                handoffs=["crm_billing", "product_promotions", "security_authentication"],  
                tools=tools,  
                system_message=(  
                    "You are the Coordinator Agent.\n"  
                    "- Your ONLY task is domain detection and routing.\n"  
                    "- Read the **user's latest message** and decide which specialist\n"  
                    "  is best suited:\n"  
                    "    • crm_billing              – invoices, payments, subscriptions\n"  
                    "    • product_promotions       – product catalogue, promos, offers\n"  
                    "    • security_authentication  – login issues, lockouts, incidents\n"  
                    "- If user’s request is unclear ask a clarifying question.\n"  
                    "- Handoff exactly ONE specialist by replying with:\n"  
                    "      HANDOFF: <specialist_name>\n"  
                    "- Never perform the specialist work yourself.\n"  
                    "- When you believe the overall conversation is complete, reply\n"  
                    "  directly to the user with your synthetic answer prefixed by\n"  
                    "  FINAL_ANSWER: <your response> and do NOT handoff."  
                ),  
            )  
  
            crm_billing = AssistantAgent(  
                name="crm_billing",  
                model_client=model_client,  
                handoffs=["coordinator"],  
                tools=tools,  
                system_message=(  
                    "You are the CRM & Billing Specialist.\n"  
                    "- Handle questions about invoices, payments, subscriptions,\n"  
                    "  refunds and billing‑related policies.\n"  
                    "- Work and chat **directly with the user**.\n"  
                    "- If the user request is outside billing / subscription scope,\n"  
                    "  immediately handoff by replying with\n"  
                    "      HANDOFF: coordinator\n"  
                    "- When you finish *all* billing‑related help, or when user says\n"  
                    "  they are satisfied, finish with\n"  
                    "      FINAL_ANSWER: <your answer>"  
                ),  
            )  
  
            product_promotions = AssistantAgent(  
                name="product_promotions",  
                model_client=model_client,  
                handoffs=["coordinator"],  
                tools=tools,  
                system_message=(  
                    "You are the Product & Promotions Specialist.\n"  
                    "- Provide product availability, features, promotional offers,\n"  
                    "  discounts and eligibility details.\n"  
                    "- Work **directly with the user**.\n"  
                    "- Handoff back to coordinator if user veers outside this domain.\n"  
                    "- Conclude with FINAL_ANSWER: … when done."  
                ),  
            )  
  
            security_authentication = AssistantAgent(  
                name="security_authentication",  
                model_client=model_client,  
                handoffs=["coordinator"],  
                tools=tools,  
                system_message=(  
                    "You are the Security & Authentication Specialist.\n"  
                    "- Troubleshoot login failures, MFA problems, account lockouts,\n"  
                    "  and provide security incident guidance.\n"  
                    "- Chat directly with user.\n"  
                    "- If the request is unrelated to security/auth, handoff back to\n"  
                    "  coordinator.\n"  
                    "- Finish with FINAL_ANSWER: … when everything is resolved."  
                ),  
            )  
  
            # 4. ───────────────  Assemble SWARM  ──────────────────────────────  
            participants: List[AssistantAgent] = [  
                coordinator,  
                crm_billing,  
                product_promotions,  
                security_authentication,  
            ]  
  
            self.team_agent = Swarm(  
                participants=participants,  
                termination_condition=termination_condition,  
                allow_repeated_speaker=True,  # let the same agent talk multiple times  
            )  
  
            # 5. ───────────────  Restore persisted state (if any)  ────────────  
            if self.state:  
                await self.team_agent.load_state(self.state)  
  
            self._initialized = True  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainRouterAgent] Initialisation failure: {exc}")  
            raise  # propagate so caller is aware  
  
    # ────────────────────────────────────────────────────────────────────────  
    #                             CHAT ENTRY‑POINT  
    # ────────────────────────────────────────────────────────────────────────  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Execute the multi‑domain SWARM for a given user prompt.  
  
        Parameters  
        ----------  
        prompt : str  
            The raw user message.  
  
        Returns  
        -------  
        str  
            The (possibly final) answer that was last produced in the run.  
        """  
        await self._setup_team_agent()  
  
        try:  
            # run the SWARM until a termination condition fires  
            response = await self.team_agent.run(  
                task=prompt,  
                cancellation_token=CancellationToken(),  
            )  
  
            assistant_response: str = response.messages[-1].content  
            # Strip leading FINAL_ANSWER label for UI continuity  
            assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()  
  
            # Persist to external chat history for UI / analytics  
            self.append_to_chat_history(  
                [  
                    {"role": "user", "content": prompt},  
                    {"role": "assistant", "content": assistant_response},  
                ]  
            )  
  
            # Persist internal state so session can resume later  
            new_state = await self.team_agent.save_state()  
            self._setstate(new_state)  
  
            return assistant_response  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainRouterAgent] chat_async error: {exc}")  
            return (  
                "Apologies, an unexpected error occurred while processing your "  
                "request. Please try again later."  
            )  