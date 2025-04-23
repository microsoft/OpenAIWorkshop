import os  
from dotenv import load_dotenv  
from typing import Any
from pathlib import Path
  
# Prior references for Autogen, cleanup later 
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import RoundRobinGroupChat  
from autogen_agentchat.conditions import TextMessageTermination  
from autogen_core import CancellationToken  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  

# Add references for AgentService
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FilePurpose, CodeInterpreterTool


  
from agents.base_agent import BaseAgent    
load_dotenv()  

# Set up the environment variables for Agent Service
PROJECT_CONNECTION_STRING= os.getenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

# Display the data to be analyzed
# Remove this later
script_dir = Path(__file__).parent  # Get the directory of the script
file_path = script_dir / 'data.txt'

with file_path.open('r') as file:
    data = file.read() + "\n"
    print(data)

# Connect to the Azure AI Foundry project
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential
        (exclude_environment_credential=True,
        exclude_managed_identity_credential=True),
    conn_str=PROJECT_CONNECTION_STRING
)




  
class Agent(BaseAgent):  
    def __init__(self, state_store, session_id) -> None:  
        super().__init__(state_store, session_id)  
        self.loop_agent = None  
        self._initialized = False  
  
    async def _setup_loop_agent(self) -> None:  
        """Initialize the assistant and tools once."""  
        if self._initialized:  
            return  
  
        server_params = SseServerParams(  
            url=self.mcp_server_uri,  
            headers={"Content-Type": "application/json"},  
            timeout=30  
        )  
        
        with project_client:

            # Upload a data file for Agent Service
            # Replace this part and point to db file later
            file = project_client.agents.upload_file_and_poll(
                file_path=file_path, purpose=FilePurpose.AGENTS
            )
            print(f"Uploaded {file.filename}")

            # Create a CodeInterpreterTool in Agent Service
            code_interpreter = CodeInterpreterTool(file_ids=[file.id])

            # Define an agent that uses the CodeInterpreterTool in AI Agent
            agent = project_client.agents.create_agent(
                model=MODEL_DEPLOYMENT,
                name="agent-service-assistant",
                instructions="You are a helpful assistant. Use all the tools at your disposal to answer questions. You cna ask clarifying questions if the user is not clear.",
                tools=code_interpreter.definitions,
                tool_resources=code_interpreter.resources,
            )
            print(f"Using agent: {agent.name}")

            # Create a thread for the conversation in AI Agent
            thread = project_client.agents.create_thread()

            # Get input prompt from the user
            user_prompt = input("Enter a prompt (or type 'quit' to exit): ")

            # Send prompt to the agent
            message = project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_prompt,
            )

            # Run agent and process the message
            run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)

 # Loop until the user types 'quit'
        while True:
            # Get input text
            user_prompt = input("Enter a prompt (or type 'quit' to exit): ")
            if user_prompt.lower() == "quit":
                break
            if len(user_prompt) == 0:
                print("Please enter a prompt.")
                continue

            






    async def chat_async(self, prompt: str) -> str:  
        """Ensure agent/tools are ready and process the prompt."""  
        await self._setup_loop_agent()  
  
        response = await self.loop_agent.run(task=prompt, cancellation_token=CancellationToken())  
        assistant_response = response.messages[-1].content  
  
        messages = [  
            {"role": "user", "content": prompt},  
            {"role": "assistant", "content": assistant_response}  
        ]  
        self.append_to_chat_history(messages)  
  
        # Update/store latest agent state  
        new_state = await self.loop_agent.save_state()  
        self._setstate(new_state)  
  
        return assistant_response  