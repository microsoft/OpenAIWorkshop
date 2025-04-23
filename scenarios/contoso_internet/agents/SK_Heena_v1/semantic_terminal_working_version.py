import asyncio
import dotenv

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin

"""
The following sample demonstrates how to create a chat completion agent that
answers customer questions around orders/billing using Semantic Kernel plugins
sourced from an async SSE MCP service that wraps Contoso APIs. 

It uses the Azure OpenAI service to create the agent, so make sure to 
set the required environment variables for the Azure AI Foundry service:
- AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
- AZURE_OPENAI_API_KEY 
- AZURE_OPENAI_ENDPOINT 
- AZURE_OPENAI_API_VERSION 
If this is not set, it will try to use DefaultAzureCredential.

"""

USER_INPUTS = [
    "I noticed my last invoice was higher than usual. Can you help me understand why? My customer id is 101",
    "What can I do to reduce my bill?",
]

async def main():
    # Load environment variables from .env file
    dotenv.load_dotenv()

    # 1. Create the agent
    async with MCPSsePlugin(
        name="ContosoMCP",
        description="Contoso MCP Plugin",
        url="http://localhost:8000/sse",
        headers={"Content-Type": "application/json"},
        timeout=30,
    ) as contoso_plugin:
        agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="ChatBot",
            instructions="You are a helpful assistant. You can use multiple tools to find information "
                        "and answer questions. Review the tools available under the MCPTools plugin "
                        "and use them as needed. You can also ask clarifying questions if the user is not clear.",
            plugins=[contoso_plugin],
        )

        for user_input in USER_INPUTS:
            # 2. Create a thread to hold the conversation
            # If no thread is provided, a new thread will be
            # created and returned with the initial response
            thread: ChatHistoryAgentThread | None = None

            print(f"### User: {user_input}")
            # 3. Invoke the agent for a response
            response = await agent.get_response(messages=user_input, thread=thread)
            print(f"### {response.name}: {response}")
            thread = response.thread

            # 4. Cleanup: Clear the thread
            await thread.delete() if thread else None

if __name__ == "__main__":
    asyncio.run(main())
