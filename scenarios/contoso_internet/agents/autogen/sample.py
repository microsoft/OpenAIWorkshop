import asyncio
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams,mcp_server_tools

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken

from dotenv import load_dotenv  
import os

load_dotenv()

azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")


async def main() -> None:
    # Create server params for the remote MCP service
    server_params = SseServerParams(
        url="https://mcp-backend-service.whiteriver-85d61b9b.westus.azurecontainerapps.io/sse",
        headers={"Content-Type": "application/json"},
        timeout=30,  # Connection timeout in seconds
    )

    # Get the translation tool from the server
    tools = await mcp_server_tools(server_params)


    # Create an agent that can use the translation tool
    model_client = AzureOpenAIChatCompletionClient(
     api_key=azure_openai_key, azure_endpoint=azure_openai_endpoint, api_version = api_version,
    azure_deployment = azure_deployment,
    model="gpt-4o-2024-11-20",
)
    agent = AssistantAgent(
        name="ai_assistant",
        model_client=model_client,
        tools=tools,
        system_message="You are a helpful assistant. Use the tools to answer the user's questions. Be diligent and thorough " 
    )

    # Let the agent translate some text
    await Console(
        agent.run_stream(task="What's the cancellation policy?", cancellation_token=CancellationToken())
    )


if __name__ == "__main__":
    asyncio.run(main())
