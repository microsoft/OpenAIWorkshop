import os  
import asyncio
from dotenv import load_dotenv  
from typing import Any
from pathlib import Path

# Add BaseAgent 
from base_agent import BaseAgent 

# Add Semantic Kernel Modules as it looks like AIAS uses SK for MCP
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
  
# Add modules for AgentService
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FilePurpose, CodeInterpreterTool
  
load_dotenv()  

# Set up the environment variables for AgentService, some duplication here, keep for now
PROJECT_CONNECTION_STRING= os.getenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")


class AIASAgent(BaseAgent):
    def __init__(self, state_store, session_id) -> None:
        super().__init__(state_store, session_id)
        self._agent = None
        self._initialized = False

    async def _setup_agent(self) -> None:
        if self._initialized:
            return
        
        # Initial Azure AI Agent Service and use MCP service
        async with MCPSsePlugin(
            name="AIASMCP",
            description="AIAS MCP Plugin",
            url=self.mcp_server_uri,
            instructions="You are a helpful assistant",
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True,
            ),
            project_connection_string=PROJECT_CONNECTION_STRING,
        ) as azure_ai_plugin:
            self._agent = ChatCompletionAgent(
                kernel=azure_ai_plugin,
                chat_history=ChatHistoryAgentThread(), #create thread for agent
                chat_completion=AzureChatCompletion(
                    azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                    azure_openai_api_base=os.getenv("AZURE_OPENAI_API_ENDPOINT"),
                    azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
                ),
            )

    
        # for when initialization is complete
        self._initialized = True
    
        async def chat_async(self, prompt: str) -> str:
            # Ensure agent/tools are ready and process the prompt.
            await self._setup_agent()

            response = await self._agent.get_response(messages=prompt, thread=self._thread)
            response_content = str(response.content)

            self._thread = response.thread
            if self._thread:
                self._setstate({"thread": self._thread})

            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_content},
            ]
            self.append_to_chat_history(messages)

            return response_content
    