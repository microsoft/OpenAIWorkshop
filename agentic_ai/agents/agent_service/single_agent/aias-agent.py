import os  
from dotenv import load_dotenv  
from typing import Any
from pathlib import Path
  
# Add references for AgentService
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FilePurpose, CodeInterpreterTool
  
load_dotenv()  

# Set up the environment variables for AgentService
PROJECT_CONNECTION_STRING= os.getenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

# For now, use a sample data.txt file for testing
# switch to using contoso.db via mcp server later
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

with project_client:

        # Upload the data file and create a CodeInterpreterTool in AI Agent
        file = project_client.agents.upload_file_and_poll(
             file_path=file_path, purpose=FilePurpose.AGENTS
        )
        print(f"Uploaded {file.filename}")

        code_interpreter = CodeInterpreterTool(file_ids=[file.id])

        # Define an agent that uses the CodeInterpreterTool in AI Agent
        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT,
            name="aias-agent",
            instructions="You are a helpful assistant. You can use multiple tools to find information and answers questions. You can also ask clarifying questions",
            tools=code_interpreter.definitions,
            tool_resources=code_interpreter.resources,
        )
        print(f"Using agent: {agent.name}")

        # Create a thread for the conversation in AI Agent
        thread = project_client.agents.create_thread()
    
        # Loop until the user types 'quit'
        while True:
            # Get input text
            user_prompt = input("Enter a prompt (or type 'quit' to exit): ")
            if user_prompt.lower() == "quit":
                break
            if len(user_prompt) == 0:
                print("Please enter a prompt.")
                continue

            # Send a prompt to the agent
            message = project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_prompt,
            )

            run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)

            # Check the run status for failures
            if run.status == "failed":
                print(f"Run failed: {run.last_error}")
    
            # Show the latest response from the agent
            messages = project_client.agents.list_messages(thread_id=thread.id)
            last_msg = messages.get_last_text_message_by_role("assistant")
            if last_msg:
                print(f"Last Message: {last_msg.text.value}")

        # Get the conversation history
        print("\nConversation Log:\n")
        messages = project_client.agents.list_messages(thread_id=thread.id)
        for message_data in reversed(messages.data):
            last_message_content = message_data.content[-1]
            print(f"{message_data.role}: {last_message_content.text.value}\n")


        # Get any generated files
        for file_path_annotation in messages.file_path_annotations:
            project_client.agents.save_file(file_id=file_path_annotation.file_path.file_id, file_name=Path(file_path_annotation.text).name)
            print(f"File saved as {Path(file_path_annotation.text).name}")

        # Clean up
        project_client.agents.delete_agent(agent.id)
        project_client.agents.delete_thread(thread.id)
    


if __name__ == '__main__': 
    main()

