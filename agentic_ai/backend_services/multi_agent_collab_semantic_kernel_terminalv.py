import asyncio
import dotenv

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin

USER_INPUTS = [
    "I noticed my last invoice was higher than usual. Can you help me understand why? My customer id is 101",
    "What can I do to reduce my bill?",
]

async def main():
    dotenv.load_dotenv()

    async with MCPSsePlugin(
        name="ContosoMCP",
        description="Contoso MCP Plugin",
        url="http://localhost:8000/sse",
        headers={"Content-Type": "application/json"},
        timeout=30,
    ) as contoso_plugin:

        # Define specialized agents
        primary_agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="primary_agent",
            instructions="You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
            "Review the tools available to you and use them as needed. You can also ask clarifying questions if "  
            "the user is not clear." ,
            plugins=[contoso_plugin]
        )

        critic_agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="CriticAgent",
            instructions="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
            plugins=[contoso_plugin]
        )

        # Triage agent decides and presents the final answer
        triage_agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="TriageAgent",
            instructions=(
                "You coordinate between PrimaryAgent and CriticAgent. "
                "First, get the response from PrimaryAgent, then ask CriticAgent to review it. "
                "Finally, present the improved response to the user if needed."
            ),
            plugins=[primary_agent, critic_agent]
        )

        for user_input in USER_INPUTS:
            thread: ChatHistoryAgentThread | None = None
            print(f"\n### User: {user_input}")

            response = await triage_agent.get_response(messages=user_input, thread=thread)
            print(f"### {response.name}: {response}")
            thread = response.thread

            await thread.delete() if thread else None

if __name__ == "__main__":
    asyncio.run(main())
