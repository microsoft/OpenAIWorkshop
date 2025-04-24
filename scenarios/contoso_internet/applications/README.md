# AI Multi-Agent MCP Chat Assistant  
  
This project is an **AI chat assistant** powered by advanced Azure OpenAI GPT models, with flexible agent configurations (including multi-agent and single-agent modes), and deep integration with external toolchains provided via the MCP Server. It consists of a FastAPI backend for session/chat management and a Streamlit frontend for easy interaction.  
  
---  
  
## Features  
- **Latest Azure OpenAI GPT models** (configurable, e.g. GPT-4.1, GPT-4o) as LLM backend  
- **MCP Server tool** integration for enhanced agent capabilities  
- **Flexible agent architecture**:  
  - Single agent, multi-agent, or reflection agent (agent module is selectable via `.env`)  
  - Agents can self-loop, collaborate, reflect, or select roles as coded in agent modules  
- **Session-based chat** with persistable conversation history  
- **FastAPI backend** with REST endpoints for chat/reset/history  
- **Modern Streamlit web frontend** for real-time chat, session reset, and history viewing  
- **Environment-based configuration** via `.env`  
  
---  
  
    
## Setup & Installation  
  

  
### 1. Clone the Repository  
  
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
- `semantic-kernel`
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
BACKEND_URL="http://localhost:8000/chat"  # only for frontend config; optional  
# AGENT_MODULE="agents.autogen.multi_agent.reflection_agent"
# AGENT_MODULE="agents.autogen.single_agent.loop_agent"
# AGENT_MODULE="agents.autogen.multi_agent.collaborative_multi_agent_round_robin"
AGENT_MODULE="agents.autogen.multi_agent.collaborative_multi_agent_selector_group"
MCP_SERVER_URI="https://mcp-backend-service.whitefield-2abc17d9.westus.azurecontainerapps.io/sse"

```
**Note:**    
- Make sure your Azure resources are configured to use the correct model deployment names, endpoints, and API versions.  
- You need access to a running **MCP Server** with the necessary tool plugins.  
  
---  
  
## Running the Application  
  
### Option 1: Run Both Backend and Frontend Together  
  
```bash  
bash run_application.sh  
```
This script will start the FastAPI backend (`backend.py`) and the Streamlit frontend (`frontend.py`) simultaneously.  
  
- The backend will listen on [http://localhost:7000](http://localhost:7000).  
- The Streamlit user interface will open (usually at [http://localhost:8501](http://localhost:8501)).  
### Option 2: Run Backend and Frontend Separately

### 1. Start the FastAPI Backend  
  
```bash  
python backe d.py  
```
The backend will be available at `http://localhost:7000/chat`.  
  
### 2. Start the Streamlit Frontend  
  
```bash  
streamlit run frontend.py  
```
Navigate to the address Streamlit provides (typically http://localhost:8501) to use the chat interface.  
  
## How It Works  
  
1. **Web UI (Streamlit):**    
   Users input messages and interact with the assistant. A unique session ID is generated for each chat session.  
  
2. **Backend (FastAPI):**    
   Receives user prompts, manages the session and in-memory chat history, and retrieves or creates an agent according to the environment setting.  
  
3. **Agent (specified by AGENT_MODULE):**    
   Processes the input using Azure OpenAI and optional MCP tools. The agent may operate in single, multi-agent, or collaborative modes, depending on configuration.  
  
4. **Chat History:**    
   Conversation history is stored per session and can be displayed in the frontend or reset as needed.  
  
---  
  
## FastAPI Endpoints  
  
- `POST /chat`    
  Send a JSON payload with `{ "session_id": ..., "prompt": ... }`. Returns the assistant’s response.  
  
- `POST /reset_session`    
  Send a payload `{ "session_id": ... }` to clear the conversation history for that session.  
  
- `GET /history/{session_id}`    
  Fetches all previous messages for a given session.  
  
---  
  
## Notes & Best Practices  
  
- The current session store uses an in-memory Python dictionary; for production deployments, substitute this with a persistent store such as Redis or a database.  
- Ensure secrets in your `.env` file (like API keys) are never committed to version control.  
- The MCP server and Azure endpoint URLs must be accessible from the backend.  
- To experiment with different agent behaviors, adjust the `AGENT_MODULE` in `.env`.  
  
---  
  
## Credits  
  
- **Microsoft Azure OpenAI Service**  
- **MCP Project**  
- **AutoGen**  
    
  
---    
## Acknowledgments  
  
- Microsoft Azure OpenAI Service    
- MCP Project    
- AutoGen    
