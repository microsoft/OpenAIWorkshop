import asyncio
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams,mcp_server_tools
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMessageTermination,TextMentionTermination

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
openai_model_name = os.getenv("OPENAI_MODEL_NAME")
async def main() -> None:
    # Create server params for the remote MCP service
    server_params = SseServerParams(
        url=mcp_server_uri,
        headers={"Content-Type": "application/json"},
        timeout=30,  # Connection timeout in seconds
    )

    # Get the translation tool from the server
    tools = await mcp_server_tools(server_params)



    # Set up the OpenAI/Azure model client  
    model_client = AzureOpenAIChatCompletionClient(  
        api_key=azure_openai_key,  
        azure_endpoint=azure_openai_endpoint,  
        api_version=api_version,  
        azure_deployment=azure_deployment,  
        model=openai_model_name,  
    )  
    # Set up the assistant agent  
    primary_agent = AssistantAgent(  
        name="primary",  
        model_client=model_client,  
        tools=tools,  
        system_message=(  
            "You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
            "Review the tools available to you and use them as needed. You can also ask clarifying questions if "  
            "the user is not clear."  
        )  
    )  
    critic_agent = AssistantAgent(  
        name="critic",  
        model_client=model_client,  
        tools=tools,  
        system_message="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
    )  

    # Termination condition: stop when critic agent approves the primary agent's response 
    termination_condition = TextMentionTermination("APPROVE")  

    team_agent = RoundRobinGroupChat(  
        [primary_agent, critic_agent],  
        termination_condition=termination_condition,  
    )  
    # Run the team with a task and print the messages to the console.
    request ="I noticed my last invoice was higher than usual—can you help me understand why and what can be done about it? my customer id is 251"
    async for message in team_agent.run_stream(task=):  # type: ignore
        print(type(message).__name__, message)
    result = await team_agent.run(task=request)
    print(result)



if __name__ == "__main__":
    asyncio.run(main())
