import os  
from dotenv import load_dotenv  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.messages import TextMessage  
from autogen_agentchat.teams import RoundRobinGroupChat  
from autogen_agentchat.conditions import TextMessageTermination  
from autogen_core import CancellationToken  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  
  
# Ensure environment is loaded every time  
load_dotenv()  
  
class Agent:  
    def __init__(self, state=None) -> None:  
        # Load Azure/OpenAI/MCP configuration from environment  
        self.azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")  
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")  
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")  
        self.mcp_server_uri = os.getenv("MCP_SERVER_URI")  
        # self.loop_agent and others will be set during async init  
        self.loop_agent = None  
        self._initialized = False  
        self.state = state
  
    async def _ensure_initialized(self):  
        # Only initialize once per instance  
        if self._initialized:  
            return  
  
        server_params = SseServerParams(  
            url=self.mcp_server_uri,  
            headers={"Content-Type": "application/json"},  
            timeout=30  
        )  
        # Get the translation tool from the server (async)  
        tools = await mcp_server_tools(server_params)  
  
        # Set up the OpenAI/Azure model client  
        model_client = AzureOpenAIChatCompletionClient(  
            api_key=self.azure_openai_key,  
            azure_endpoint=self.azure_openai_endpoint,  
            api_version=self.api_version,  
            azure_deployment=self.azure_deployment,  
        )  
        # Set up the assistant agent  
        agent = AssistantAgent(  
            name="ai_assistant",  
            model_client=model_client,  
            tools=tools,  
            system_message=(  
                "You are a helpful assistant. You can use multiple tools to find information and answer questions. "  
                "Review the tools available to you and use them as needed. You can also ask clarifying questions if "  
                "the user is not clear."  
            )  
        )  
        # Termination condition: stop when agent answers as itself  
        termination_condition = TextMessageTermination("ai_assistant")  
  
        self.loop_agent = RoundRobinGroupChat(  
            [agent],  
            termination_condition=termination_condition,  
        )  
        self._initialized = True  
  
    async def chat_async(self, prompt: str) -> str: 
        # Ensure agent/tools are ready  
        await self._ensure_initialized() 
        if self.state:  
            await self.loop_agent.load_state(self.state)

        response = await self.loop_agent.run(task=prompt, cancellation_token=CancellationToken())
        return response.messages[-1].content
  
