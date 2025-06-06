import logging
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_core import CancellationToken

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools

from agents.base_agent import BaseAgent

# Define termination condition
termination_condition = TextMentionTermination("FINAL_ANSWER:") | MaxMessageTermination(max_messages=10)

class Agent(BaseAgent):
    """
    Simplified multi-agent system using Swarm architecture with 3 agents:
    • Coordinator: Routes requests to specialists
    • Billing Agent: Handles customer accounts and payments
    • Product Agent: Provides information on products and promotions
    """

    def __init__(self, state_store: dict, session_id: str) -> None:
        super().__init__(state_store, session_id)
        self.team_agent = None
        self._initialized = False

    async def _setup_team_agent(self) -> None:
        """Create the swarm team once per session."""
        if self._initialized:
            return

        try:
            # 1. Setup tools
            server_params = SseServerParams(
                url=self.mcp_server_uri,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            # HINT: One approach to improve performance is to specify which tools to use in each agent. That are domain specific.
            tools = await mcp_server_tools(server_params)

            # 2. Setup model client
            model_client = AzureOpenAIChatCompletionClient(
                api_key=self.azure_openai_key,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
                azure_deployment=self.azure_deployment,
                model=self.openai_model_name,
            )

            # 3. Create simplified agents
            # HINT: You can adjust the prompts to improve the performance. 
            coordinator = AssistantAgent(
                name="coordinator",
                model_client=model_client,
                handoffs=["billing", "product"],
                tools=tools,
                system_message=(
                    "You are the Coordinator. Route user requests to specialists.\n"
                    "Never answer the quesitons directly, route them to the right agent.\n"
                    "Ask clarifying questions if needed.\n"
                    "- For billing/account questions: @billing\n"
                    "- For product/promotion questions: @product\n"
                    "- Only provide direct answers for simple questions\n"
                    "- When answering directly, use: FINAL_ANSWER: your response"
                ),
            )

            billing_agent = AssistantAgent(
                name="billing",
                model_client=model_client,
                tools=tools,
                handoffs=["coordinator"],
                system_message=(
                    "You are the Billing Agent. Handle accounts and payments.\n"
                    "- Use tools to find billing information\n"
                    "- For non-billing questions: @coordinator\n"
                    "- When providing final answers: FINAL_ANSWER: your response"
                ),
            )

            product_agent = AssistantAgent(
                name="product",
                model_client=model_client,
                tools=tools,
                handoffs=["coordinator"],
                system_message=(
                    "You are the Product Agent. Handle product information.\n"
                    "- Use tools to find product and promotion details\n"
                    "- For non-product questions: @coordinator\n"
                    "- When providing final answers: FINAL_ANSWER: your response"
                ),
            )

            # YOU WILL NEED TO ADD A SECURITY AGENT THAT IS SPECIALIZED IN HANDLING SECURITY RELATED QUESTIONS.
            # security_agent = AssistantAgent(


            # 4. Create the swarm
            self.team_agent = Swarm(
                participants=[coordinator, billing_agent, product_agent],
                termination_condition=termination_condition,
            )

            # 5. Restore state if available
            if self.state:
                await self.team_agent.load_state(self.state)

            self._initialized = True

        except Exception as exc:
            logging.error(f"Initialization error: {exc}")
            raise

    async def chat_async(self, prompt: str) -> str:
        await self._setup_team_agent()

        try:
            # Run the conversation
            response = await self.team_agent.run(
                task=prompt,
                cancellation_token=CancellationToken(),
            )

            # Extract the final response
            assistant_response = response.messages[-1].content
            
            # Remove FINAL_ANSWER prefix if present
            if "FINAL_ANSWER:" in assistant_response:
                assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()

            # Update chat history
            self.append_to_chat_history([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_response},
            ])

            # Save state for next turn
            self._setstate(await self.team_agent.save_state())

            return assistant_response

        except Exception as exc:
            logging.error(f"Chat error: {exc}")
            return "Sorry, an error occurred. Please try again."