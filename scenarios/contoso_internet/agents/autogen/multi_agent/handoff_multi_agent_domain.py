import sys
import os
# Add the project root to sys.path
sys.path.insert(0, "c:/Users/crehfuss/Projects/agents/OpenAIWorkshop")

import logging
from typing import Any, List
import json

from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMessageTermination, TextMentionTermination, MaxMessageTermination 
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  

from scenarios.contoso_internet.agents.base_agent import BaseAgent

# Define termination conditions
text_mention_termination = TextMentionTermination("FINAL_ANSWER")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination_condition = text_mention_termination | max_messages_termination

class Agent(BaseAgent):  
    """  
    Collaborative multi-agent system using Swarm architecture.
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
            # 1. Shared Tooling (Knowledge Base access)
            server_params = SseServerParams(  
                url=self.mcp_server_uri,  
                headers={"Content-Type": "application/json"},  
                timeout=30,  
            )  
            
            tools = await mcp_server_tools(server_params)
            
            # 2. Shared Model Client
            model_client = AzureOpenAIChatCompletionClient(  
                api_key=self.azure_openai_key,  
                azure_endpoint=self.azure_openai_endpoint,  
                api_version=self.api_version,  
                azure_deployment=self.azure_deployment,  
                model=self.openai_model_name,  
            )
  
            # 3. Agent Definitions
            coordinator = AssistantAgent(  
                name="coordinator",  
                model_client=model_client,  
                handoffs=["crm_billing", "product_promotions", "security_authentication"],  
                tools=tools,  
                system_message=(  
                    "You are the Coordinator Agent.\n"  
                    "- Your main role is to engage with the user to understand their intent.\n"  
                    "- Begin each conversation by asking clarifying questions if the user's needs are not clear.\n"  
                    "- Once you have identified the user's domain or specific request, hand off the conversation to a single appropriate specialist agent.\n"  
                    "- When handing off, use the @agent_name format like: @crm_billing I'm handing this billing inquiry to you.\n"  
                    "- Do not use 'HANDOFF:' format as it may cause problems with the system.\n"
                    "- You can handoff to crm_billing, product_promotions, security_authentication agents only. \n"
                    "- Do not attempt to solve the user's problem yourself or perform the work of a specialist.\n"  
                    "- If the user's request is ambiguous or missing information, ask follow-up questions until you understand enough to route correctly.\n"  
                    "- If, at any time, the conversation is complete and a final response is appropriate, reply to the user directly. In this case, prefix your message with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                    "- At all times, avoid bottlenecks by only routing and clarifying; never perform specialist tasks."  
                ),  
            )    

            crm_billing_agent = AssistantAgent(  
                name="crm_billing",  
                description="Agent specializing in customer account, subscription, billing inquiries, invoices, payments, and related policy checks.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the CRM & Billing Agent.\n"  
                    "- Query structured CRM / billing systems for account, subscription, "  
                    "invoice, and payment information as needed.\n"  
                    "- Always Check *Knowledge Base* articles on billing policies, payment "  
                    "processing, refund rules, etc., to ensure responses are accurate "  
                    "and policy-compliant. You can access these with the tools. \n"  
                    "- Suggest solutions to user if you see a potential issue, confirm before you act.\n"
                    "- If the user's request is ambiguous or missing information, ask follow-up questions until you understand \n"
                    "- You should use multiple tools to find information and answer questions. "  
                    "- Review the tools available to you and use them as needed. Use the tools\n"    
                    "when CRM or billing topics arise.\n" 
                    "- If you receive a question outside of your domain of CRM / billing handoff to the coordinator. \n"
                    "- If, at any time, the conversation is complete and a final response is appropriate, reply to the user directly. Sythasize all the information you've learned and prefix your message with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                ),  
            )  

            product_promotions_agent = AssistantAgent(  
                name="product_promotions",  
                description="Agent for retrieving and explaining product availability, promotions, discounts, eligibility, and terms.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the Product & Promotions Agent.\n"  
                    "- Retrieve promotional offers, product availability, eligibility "  
                    "criteria, and discount information from structured sources.\n"  
                    "- Always augment answers with *Knowledge Base* FAQs, terms & conditions, "  
                    "and best practices. You can access these with the tools.\n" 
                    "- Suggest solutions to user if you see a potential issue or solution, do not act without confirmation.\n"
                    "- If the user's request is ambiguous or missing information, ask follow-up questions until you understand \n" 
                    "- You should use multiple tools to find information and answer questions. "  
                    "- Review the tools available to you and use them as needed.\n"    
                    "- If you receive a question outside of your domain of product and promotion handoff to the coordinator. \n"
                    "- If, at any time, the conversation is complete and a final response is appropriate, reply to the user directly. Sythasize all the information you've learned and prefix your message with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                ),  
            )  

            security_authentication_agent = AssistantAgent(  
                name="security_authentication",  
                description="Agent focusing on security, authentication issues, lockouts, account security incidents, providing risk assessment and mitigation guidance.",  
                model_client=model_client,  
                tools=tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the Security & Authentication Agent.\n"  
                    "- Investigate authentication logs, account lockouts, and security "  
                    "incidents in structured security databases.\n"  
                    "- Always cross-reference *Knowledge Base* security policies and "  
                    "lockout troubleshooting guides with your tools.\n" 
                    "- Suggest solutions to user if you see a potential issue, do not act unless you have confirmation.\n" 
                    "- If the user's request is ambiguous or missing information, ask follow-up questions until you understand \n"
                    "- You should use multiple tools to find information and answer questions. "  
                    "- Review the tools available to you and use them as needed.\n"  
                    "- If you receive a question outside of your domain of security handoff to the coordinator. \n"
                    "- If, at any time, the conversation is complete and a final response is appropriate, reply to the user directly. Sythasize all the information you've learned and prefix your message with:\n"  
                    "      FINAL_ANSWER: <your response>\n"   
                ),  
            )    
            
            # 4. Assemble Swarm Team
            participants: List[AssistantAgent] = [  
                coordinator,  # coordinator should be first
                crm_billing_agent,  
                product_promotions_agent,  
                security_authentication_agent,  
            ]  
  
            # Create the swarm with the coordinator as the first agent
            self.team_agent = Swarm(  
                participants=participants,
                termination_condition=termination_condition,
            )
                 
            # 5. Restore persisted state (if any)
            if self.state:  
                await self.team_agent.load_state(self.state)  
  
            self._initialized = True  
  
        except Exception as exc:  
            raise  # Re-raise so caller is aware something went wrong  
  
    async def chat_async(self, prompt: str) -> str:
        await self._setup_team_agent()

        try:
            # Run the conversation with the user prompt
            response = await self.team_agent.run(
                task=prompt,
                cancellation_token=CancellationToken(),
            )

            # Extract the final response
            assistant_response: str = response.messages[-1].content
            assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()
            
            # Persist interaction in chat history
            self.append_to_chat_history(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": assistant_response},
                ]
            )

            # Persist internal state
            new_state = await self.team_agent.save_state()
            self._setstate(new_state)
        
            return assistant_response

        except Exception as exc:
            return (
                "Apologies, an unexpected error occurred while processing your "
                "request. Please try again later."
            )