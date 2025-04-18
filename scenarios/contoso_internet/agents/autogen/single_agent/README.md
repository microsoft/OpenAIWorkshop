# AI Agent MCP Chat Assistant  
  
This project is a **single-agent AI chat assistant** that utilizes advanced Azure OpenAI GPT models and external tools provided via the MCP Server. The agent is designed to autonomously use its own reasoning and integrated toolset to research and propose solutions based on user prompts.   
  
Key features:  
  
- Uses Azure OpenAI GPT (e.g., GPT-4o) as the main LLM backend  
- Integrates **MCP server tools**  
- Agent can self-loop and reason through multiple steps until a solution is found  
- Supports session-based chat history and multi-turn conversations via FastAPI backend  
- Streamlit frontend for a user-friendly chat experience  
  
---  
  
## How it works  
  
1. **User** sends a message using the web (Streamlit) UI.  
2. **Backend** (FastAPI) receives the prompt, manages agent state per session, and routes input to the agent.  
3. **Agent** uses Azure OpenAI API and MCP-provided tools to autonomously solve the task; it may interact with its own internal tool loop if needed.  
4. **Response** is displayed in the chat interface.  
  
---  
  
## Setup & Installation  
  
### 1. Clone the Repository  
  
```bash  
git clone https://github.com/your-repository/ai-agent-mcp-chat.git  
cd ai-agent-mcp-chat  
```

### 2. Install Python dependencies  
  
It is recommended to use a virtual environment.  
  
```bash  
python -m venv venv  
source venv/bin/activate   # On Windows: venv\Scripts\activate  
pip install -r requirements.txt  

```

#### Example `requirements.txt` includes:  
  
- `flask`  
- `faker`  
- `python-dotenv`  
- `tenacity`  
- `openai`  
- `flasgger`  
- `fastmcp`  
- `autogen-ext[mcp]`  
- `autogen-agentchat`  
- `uvicorn`  
- `fastapi`  
- `streamlit`  
- `requests`  
- `pydantic`  
- *(Add others as needed for your specific environment)*  
  
---  
  
### 3. Set up your environment variables  
  
Rename `.env.sample` to `.env` and fill in all required fields:  
  
```env  
AZURE_OPENAI_ENDPOINT="https://<your-endpoint>.openai.azure.com"  
AZURE_OPENAI_API_KEY="<your-azure-api-key>"  
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4o"  
AZURE_OPENAI_API_VERSION="2025-03-01-preview"  
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-ada-002"  
MCP_SERVER_URI="https://<your-mcp-backend>/sse"  
BACKEND_URL="http://localhost:8000/chat"  # only for frontend config; optional  
```
**Note:**    
- Make sure your Azure resources are configured to use the correct model deployment names, endpoints, and API versions.  
- You need access to a running **MCP Server** with the necessary tool plugins.  
  
---  
  
## Running the Application  
  
### 1. Start the FastAPI Backend  
  
```bash  
python server.py  
```
The backend will be available at `http://localhost:8000/chat`.  
  
### 2. Start the Streamlit Frontend  
  
```bash  
streamlit run frontend.py  
```
Navigate to the address Streamlit provides (typically http://localhost:8501) to use the chat interface.  
  
## Application Structure  
  
- `agent.py`    
  Implements an agent class with self-looping and tool integration via the MCP server.  
  
- `server.py`    
  FastAPI backend for managing chat sessions and routing prompts to the agent.  
  
- `frontend.py`    
  Streamlit-based UI for chatting with the AI agent.  
  
- `.env`    
  Environment and credentials configuration.  
  
---  
  
## Notes & Troubleshooting  
  
- To run this in production, replace the in-memory session store with something persistent (e.g., Redis, a database).  
- The MCP server URL must be reachable from where the backend runs.  
- Make sure all credentials remain secret and do not commit `.env` with secrets.  
  
---  
  
  
## Acknowledgments  
  
- Microsoft Azure OpenAI Service    
- MCP Project    
- AutoGen    