import asyncio
import dotenv

from agents.base_agent import BaseAgent
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

MCP_SERVER_URI="http://localhost:8000/sse"

class Agent(BaseAgent):  
    def __init__(self, state_store, session_id) -> None:  
        super().__init__(state_store, session_id)
        self._agent = None  
        self._initialized = False 
        
    async def _setup_agent(self) -> None:
        # Initialize the assistant and tools only once. 
        if self._initialized:  
            return
        
        # Load environment variables from .env file.
        dotenv.load_dotenv()

        # Set up the SSE plugin for the MCP service.
        contoso_plugin = MCPSsePlugin(
            name="ContosoMCP",
            description="Contoso MCP Plugin",
            url=MCP_SERVER_URI,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        # Set up the chat completion agent with the Azure OpenAI service and the MCP plugin.
        self._agent = ChatCompletionAgent(
            service=AzureChatCompletion(),
            name="ChatBot",
            instructions="You are a helpful assistant. You can use multiple tools to find information "
                        "and answer questions. Review the tools available under the MCPTools plugin "
                        "and use them as needed. You can also ask clarifying questions if the user is not clear.",
            plugins=[contoso_plugin],
        )

        # Create a thread to hold the conversation.
        # If no thread is provided, a new thread will be created and returned with the initial response.
        self._thread: ChatHistoryAgentThread | None = None

        self._initialized = True  
    
    async def chat_async(self, prompt: str) -> str:  
        # Ensure agent/tools are ready and process the prompt.
        await self._setup_agent()

        response = await self._agent.get_response(messages=prompt, thread=self._thread)
        response_content = str(response.content)
        self._thread = response.thread

        messages = [  
            {"role": "user", "content": prompt},  
            {"role": "assistant", "content": response_content}  
        ]
        self.append_to_chat_history(messages)

        # Cleanup the thread async.
        await response.thread.delete() if response.thread else None
  
        return response_content  

# ## Uncomment the following lines to run the agent in a standalone mode (i.e without FastAPI backend) ###
# async def main():
#     SESSION_STORE = {} # In-memory session store (use Redis/DB for production)
#     agent = Agent(SESSION_STORE, "test_session_id")

#     SAMPLE_USER_INPUTS = [
#         "I noticed my last invoice was higher than usual. Can you help me understand why? My customer id is 101",
#         "What can I do to reduce my bill?",
#     ]

#     for user_input in SAMPLE_USER_INPUTS:
#         answer = await agent.chat_async(user_input)
#         print(f"User: {user_input}\nAssistant: {answer}\n")

# if __name__ == "__main__":
#     asyncio.run(main())
