import sys
import os
# Add the project root to sys.path
sys.path.insert(0, "c:/Users/crehfuss/Projects/agents/OpenAIWorkshop")

import logging  
from typing import Any, List  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import Swarm  # keeps implementation simple & familiar  
from autogen_agentchat.conditions import TextMessageTermination,TextMentionTermination,MaxMessageTermination 
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  

from scenarios.contoso_internet.agents.base_agent import BaseAgent

#Define termination conditions
text_mention_termination = TextMentionTermination("FINAL_ANSWER")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination_condition = text_mention_termination | max_messages_termination

class Agent(BaseAgent):  
    """  
    Collaborative multi-agent system using Swarm architecture:  
        • Analysis & Planning Agent (coordinator)  
        • CRM & Billing Agent  
        • Product & Promotions Agent  
        • Security & Authentication Agent  
  
    Each specialist has access to the central Knowledge Base through the  
    mcp_server_tools tool-suite. The Analysis & Planning Agent coordinates  
    the conversation and produces the final synthesis.
    
    Swarm allows agents to work simultaneously rather than taking turns sequentially.
    """  

    def __init__(self, state_store: dict, session_id: str) -> None:  
        super().__init__(state_store, session_id)  
        self.team_agent: Any = None  
        self._initialized: bool = False  
  
    # --------------------------------------------------------------------- #  
    #                         TEAM INITIALISATION                           #  
    # --------------------------------------------------------------------- #  
    async def _setup_team_agent(self) -> None:  
        """Create/restore the swarm team once per session."""  
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
                description="The coordinator agent that manages the overall flow, delegates tasks, and synthesizes the final answer.",  
                model_client=model_client,  
                tools=tools,
                handoffs=["crm_billing","product_promotion", "security_authentication"],
                system_message=(  
                    "You are the Analysis & Planning Agent – the orchestrator. "  
                    "Your responsibilities:\n"  
                    "1) Parse the customer's abstract request. \n" 
                    "1b) Understand the customer's intent and have agents proactively look for solutions." 
                    "2) Break it down into clear subtasks and handoff to the "  
                    "domain specialists (crm_billing, product_promotions, "  
                    "security_authentication).\n"  
                    "3) Integrate the specialists' outputs into ONE comprehensive, "  
                    "coherent answer for the customer.\n"  
                    "4) When satisfied, respond to the customer with one final answer "  
                    "prefixed by: FINAL_ANSWER:\n\n"  
                    "If you still need information, continue the dialogue with the "  
                    "specialists; otherwise finish with the final answer. \n"
                    "You can handoff to: crm_billing, product_promotions, and security_authentication agents."    
                    
                ),  
            )  

            crm_billing_agent = AssistantAgent(  
                name="crm_billing",  
                description="Agent specializing in customer account, subscription, billing inquiries, invoices, payments, and related policy checks.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["analysis_planning"],
                system_message=(  
                    "You are the CRM & Billing Agent.\n"  
                    "- Query structured CRM / billing systems for account, subscription, "  
                    "invoice, and payment information as needed.\n"  
                    "- Check *Knowledge Base* articles on billing policies, payment "  
                    "processing, refund rules, etc., to ensure responses are accurate "  
                    "and policy-compliant.\n"  
                    "- Proactively contribute relevant information to the conversation "  
                    "when CRM or billing topics arise.\n"  
                    "- Always handoff back to the analysis_planning Agent when analysis is complete. \n"  
                ),  
            )  

            product_promotions_agent = AssistantAgent(  
                name="product_promotions",  
                description="Agent for retrieving and explaining product availability, promotions, discounts, eligibility, and terms.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["analysis_planning"],
                system_message=(  
                    "You are the Product & Promotions Agent.\n"  
                    "- Retrieve promotional offers, product availability, eligibility "  
                    "criteria, and discount information from structured sources.\n"  
                    "- Augment answers with *Knowledge Base* FAQs, terms & conditions, "  
                    "and best practices.\n"  
                    "- Proactively contribute product and promotion details when relevant.\n"  
                    "- Always handoff back to the analysis_planning Agent when analysis is complete."  
                ),  
            )  

            security_authentication_agent = AssistantAgent(  
                name="security_authentication",  
                description="Agent focusing on security, authentication issues, lockouts, account security incidents, providing risk assessment and mitigation guidance.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["analysis_planning"],
                system_message=(  
                    "You are the Security & Authentication Agent.\n"  
                    "- Investigate authentication logs, account lockouts, and security "  
                    "incidents in structured security databases.\n"  
                    "- Always cross-reference *Knowledge Base* security policies and "  
                    "lockout troubleshooting guides.\n"  
                    "- Proactively contribute security insights when relevant.\n"  
                    "- Always handoff back to the analysis_planning Agent when securiy assessment is complete."  
                ),  
            )    
            
            # 4. -----------------  Assemble Swarm Team -----------------  
            participants: List[AssistantAgent] = [  
                analysis_planning_agent,  # coordinator should be first
                crm_billing_agent,  
                product_promotions_agent,  
                security_authentication_agent,  
            ]  
  
            # Create the swarm with the coordinator as the first agent
            self.team_agent = Swarm(  
                participants=participants,
                termination_condition=termination_condition,
            )
                 
            # 5. -----------------  Restore persisted state (if any) -----------------  
            if self.state:  
                await self.team_agent.load_state(self.state)  
  
            self._initialized = True  
  
        except Exception as exc:  
            logging.error(f"[SwarmMultiDomainAgent] Initialization failure: {exc}")  
            raise  # re-raise so caller is aware something went wrong  
  
    # --------------------------------------------------------------------- #  
    #                              CHAT ENTRY                               #  
    # --------------------------------------------------------------------- #  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Executes the collaborative multi-agent swarm chat for a given user prompt.  
  
        Returns  
        -------  
        str  
            The final, synthesized reply produced by the Analysis & Planning Agent.  
        """  
        await self._setup_team_agent()  
  
        try:  
            response = await self.team_agent.run(  
                task=prompt,  
                cancellation_token=CancellationToken(),  
            )  
  
            assistant_response: str = response.messages[-1].content  
            assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()
  
            # Persist interaction in chat history so UI / analytics can render it.  
            self.append_to_chat_history(  
                [  
                    {"role": "user", "content": prompt},  
                    {"role": "assistant", "content": assistant_response},  
                ]  
            )  
  
            # Persist internal Agent-Chat state for future turns / resumptions.  
            new_state = await self.team_agent.save_state()  
            self._setstate(new_state)  
  
            return assistant_response  
  
        except Exception as exc:  
            logging.error(f"[SwarmMultiDomainAgent] chat_async error: {exc}")  
            return (  
                "Apologies, an unexpected error occurred while processing your "  
                "request. Please try again later."  
            )