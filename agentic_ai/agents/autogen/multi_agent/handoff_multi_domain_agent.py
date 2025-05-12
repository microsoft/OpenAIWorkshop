import sys
import os

import logging  
from typing import Any, List  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import Swarm   
from autogen_agentchat.conditions import TextMessageTermination,TextMentionTermination,MaxMessageTermination 
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  

from agents.base_agent import BaseAgent

#Define termination conditions
text_mention_termination = TextMentionTermination("FINAL_ANSWER:")
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
            all_tools=tools.copy()  # Keep a copy of all tools for later use

            # 1.2 -----------------  Filter Tools by Domain  -----------------
            tool_categories = {
                "common": ["search_knowledge_base"],
                "crm_billing": ["get_all_customers", "get_customer_detail", "get_subscription_detail",
                               "get_invoice_payments", "pay_invoice", "get_billing_summary",
                               "create_support_ticket", "get_support_tickets"],
                "product_promotions": ["get_promotions", "get_eligible_promotions", "get_products",
                                      "get_product_detail", "get_data_usage", "get_customer_orders"],
                "security": ["get_security_logs", "unlock_account", "update_subscription"]
            }

            try:
                # Categorize tools by domain
                common_tools = [tool for tool in all_tools if hasattr(tool, 'name') 
                               and tool.name in tool_categories["common"]]
                
                crm_billing_tools = common_tools + [tool for tool in all_tools if hasattr(tool, 'name') 
                                                   and tool.name in tool_categories["crm_billing"]]
                
                product_tools = common_tools + [tool for tool in all_tools if hasattr(tool, 'name') 
                                               and tool.name in tool_categories["product_promotions"]]
                
                security_tools = common_tools + [tool for tool in all_tools if hasattr(tool, 'name') 
                                                and tool.name in tool_categories["security"]]
                
                # Log tool counts for debugging
                logging.info(f"Common tools: {len(common_tools)}, CRM: {len(crm_billing_tools)}, "
                            f"Product: {len(product_tools)}, Security: {len(security_tools)}")
                
            except Exception as e:
                logging.warning(f"Tool filtering failed: {e}. Using full toolset for all agents.")
                common_tools = crm_billing_tools = product_tools = security_tools = all_tools

            # Coordinator always gets full access
            coordinator_tools = all_tools

            # 2. -----------------  Shared Model Client -----------------  
            model_client = AzureOpenAIChatCompletionClient(  
                api_key=self.azure_openai_key,  
                azure_endpoint=self.azure_openai_endpoint,  
                api_version=self.api_version,  
                azure_deployment=self.azure_deployment,  
                model=self.openai_model_name,  
            )  
  
            # 3. -----------------  Agent Definitions -----------------  
            # 3. Agent Definitions
            coordinator = AssistantAgent(  
                name="coordinator",  
                model_client=model_client,  
                handoffs=["crm_billing", "product_promotions", "security_authentication"],  
                tools=None,  
                system_message=(  
                    "You are the Coordinator Agent.\n"  
                    "- Your main role is to engage with the user to understand their intent.\n"  
                    "- Begin each conversation by asking clarifying questions if the user's needs are not clear.\n"  
                    "- Once you have identified the user's domain or specific request, hand off the conversation to a single appropriate specialist agent.\n" 
                    "- You can handoff to crm_billing, product_promotions, security_authentication agents only. \n" 
                    "- When handing off, use the @agent_name format like: @crm_billing I'm handing this billing inquiry to you.\n"  
                    "- Do not use 'HANDOFF:' format as it may cause problems with the system.\n"
                    "- NEVER attempt to solve the user's problem yourself or perform the work of a specialist.\n"    
                    "- IMPORTANT: When performing a handoff, do NOT use FINAL_ANSWER prefix. Only use the @agent_name format.\n"
                    "- Only use FINAL_ANSWER prefix when you are providing a direct response to the user without handing off.\n"  
                    "- When not handing off, your messages to the user should be prefixed with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                    "- At all times, avoid bottlenecks by only routing and clarifying; never perform specialist tasks."  
                ),  
            )    

            crm_billing_agent = AssistantAgent(  
                name="crm_billing",  
                description="Agent specializing in customer account, subscription, billing inquiries, invoices, payments, and related policy checks.",  
                model_client=model_client,  
                tools=crm_billing_tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the CRM & Billing Agent.\n"  
                    "- Query structured CRM / billing systems for account, subscription, "  
                    "invoice, and payment information as needed.\n"  
                    "- Always Check *Knowledge Base* articles on billing policies, payment "  
                    "processing, refund rules, etc., to ensure responses are accurate "  
                    "and policy-compliant. You can access these with the tools.\n"  
                    "- IMPORTANT: Before transferring back to coordinator, you MUST attempt to use at least one tool to find information.\n"
                    "- Transfer back to coordinator ONLY if the request is clearly outside your domain after you've tried to assist.\n"
                    "- You handle all service activation, international usage, billing inquiries and account-related issues.\n"
                    "- Suggest solutions to user if you see a potential issue, ALWAYS confirm before you act.\n"
                    "- You should use multiple tools to find information and answer questions.\n"    
                    "- Review the tools available to you and use them as needed.\n"    
                    "- If you receive a question outside of your domain of CRM / billing handoff to the coordinator.\n" 
                    "- IMPORTANT: When transferring back to coordinator, do NOT use FINAL_ANSWER prefix.\n"
                    "- Only use FINAL_ANSWER prefix when you are providing a complete response directly to the user.\n"  
                    "- If you need more information from the user or are offering options, include your questions within the FINAL_ANSWER.\n"  
                    "- When providing a final response to the user (not transferring), prefix with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                ),  
            )  

            product_promotions_agent = AssistantAgent(  
                name="product_promotions",  
                description="Agent for retrieving and explaining product availability, promotions, discounts, eligibility, and terms.",  
                model_client=model_client,  
                tools=product_tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the Product & Promotions Agent.\n"  
                    "- Retrieve promotional offers, product availability, eligibility "  
                    "criteria, and discount information from structured sources.\n"  
                    "- Always augment answers with *Knowledge Base* FAQs, terms & conditions, "  
                    "and best practices. You can access these with the tools.\n" 
                    "- IMPORTANT: Before transferring back to coordinator, you MUST attempt to use at least one tool to find information.\n"
                    "- Transfer back to coordinator ONLY if the request is clearly outside your domain after you've tried to assist.\n"
                    "- Suggest solutions to user if you see a potential issue or solution, do not act without confirmation.\n"
                    "- You should use multiple tools to find information and answer questions.\n"    
                    "- Review the tools available to you and use them as needed.\n"    
                    "- If you receive a question outside of your domain of product and promotion handoff to the coordinator.\n" 
                    "- IMPORTANT: When transferring back to coordinator, do NOT use FINAL_ANSWER prefix.\n"
                    "- Only use FINAL_ANSWER prefix when you are providing a complete response directly to the user.\n"  
                    "- If you need more information from the user or are offering options, include your questions within the FINAL_ANSWER.\n"  
                    "- When providing a final response to the user (not transferring), prefix with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                ),  
            )  

            security_authentication_agent = AssistantAgent(  
                name="security_authentication",  
                description="Agent focusing on security, authentication issues, lockouts, account security incidents, providing risk assessment and mitigation guidance.",  
                model_client=model_client,  
                tools=security_tools,  
                handoffs=["coordinator"],
                system_message=(  
                    "You are the Security & Authentication Agent.\n"  
                    "- Investigate authentication logs, account lockouts, and security "  
                    "incidents in structured security databases.\n"  
                    "- Always cross-reference *Knowledge Base* security policies and "  
                    "lockout troubleshooting guides with your tools.\n"
                    "- IMPORTANT: Before transferring back to coordinator, you MUST attempt to use at least one tool to find information.\n"
                    "- Transfer back to coordinator ONLY if the request is clearly outside your domain after you've tried to assist.\n"
                    "- Suggest solutions to user if you see a potential issue, do not act unless you have confirmation.\n" 
                    "- You should use multiple tools to find information and answer questions.\n"    
                    "- Review the tools available to you and use them as needed.\n"  
                    "- If you receive a question outside of your domain of security handoff to the coordinator.\n" 
                    "- IMPORTANT: When transferring back to coordinator, do NOT use FINAL_ANSWER prefix.\n"
                    "- Only use FINAL_ANSWER prefix when you are providing a complete response directly to the user.\n"  
                    "- If you need more information from the user or are offering options, include your questions within the FINAL_ANSWER.\n"  
                    "- When providing a final response to the user (not transferring), prefix with:\n"  
                    "      FINAL_ANSWER: <your response>\n"  
                ),  
            )    
            
            # 4. -----------------  Assemble Swarm Team -----------------  
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
        await self._setup_team_agent()  
    
        try:  
            # Run the conversation
            response = await self.team_agent.run(  
                task=prompt,  
                cancellation_token=CancellationToken(),  
            )  
    
            # Simply use the last message as the response
            assistant_response: str = response.messages[-1].content
            
            # Remove FINAL_ANSWER prefix if present
            if assistant_response and "FINAL_ANSWER:" in assistant_response:
                assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()
    
            # Persist interaction in chat history
            self.append_to_chat_history([  
                {"role": "user", "content": prompt},  
                {"role": "assistant", "content": assistant_response},  
            ])  
    
            # Persist internal Agent-Chat state for future turns
            new_state = await self.team_agent.save_state()  
            self._setstate(new_state)  
    
            return assistant_response  
        
        except Exception as exc:  
            logging.error(f"[SwarmMultiDomainAgent] chat_async error: {exc}")  
            return (
                "Apologies, an unexpected error occurred while processing your "
                "request. Please try again later."  
            )