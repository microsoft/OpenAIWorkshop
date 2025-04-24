import asyncio
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams,mcp_server_tools
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMessageTermination

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_agentchat.messages import StructuredMessage, TextMessage


from dotenv import load_dotenv  
import os

load_dotenv()

azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
mcp_server_uri = os.getenv("MCP_SERVER_URI")

async def main() -> None:
    # Create server params for the remote MCP service
    server_params = SseServerParams(
        url=mcp_server_uri,
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
        system_message="You are a helpful assistant. You can use multiple tools to find information and answer questions. Review the tools available to you and use them as needed. You can also ask clarifying questions if the user is not clear.", 
    )

    termination_condition = TextMessageTermination("ai_assistant")

    # Create a team with the looped assistant agent and the termination condition.
    team = RoundRobinGroupChat(
        [agent],
        termination_condition=termination_condition,
    )

    # Run the team with a task and print the messages to the console.
    async for message in team.run_stream(task="I noticed my last invoice was higher than usual—can you help me understand why and what can be done about it? my customer id is 101"):  # type: ignore
        print(type(message).__name__, message)



if __name__ == "__main__":
    asyncio.run(main())
