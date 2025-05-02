![alt text](image-1.png)
# Microsoft AI Agentic Workshop Repository  
  
This repository has materials for latest AI Agentic Workshop from Microsoft. 

# Repository includes
1. Business scenario - **SCENARIO.md**
2. Step-by-step instructions -  **SETUP.md**
3. Agent implementations -  **agents** folder
4. Documentation on agent implementations - **AGENT_DOC.md**
5. Agent Design Patterns reference - **AGENT_PATTERNS.md**
6. Common framework all agents in this workshop use - **FRAMEWORK.md**
7. Back-end server and APIs - **applications** folder
8. Front-end app - **applications** folder
9. Common toolset in an MCP server - see **run** folder
10. Data files -  **data** folder

# Users can 
1. Design and prototype agent solutions 
2. Compare single vs multi-agent implementations 
3. Develop and compare agents using different platforms
- Azure AI Agent Service
- Semantic Kernel
- Autogen  

# Features  
- **Latest Azure OpenAI GPT models** (configurable, e.g. GPT-4.1, GPT-4o) as LLM backend  
- **MCP Server tool** integration for enhanced agent capabilities  
- **Flexible agent architecture**:  
  - Single agent, multi-agent, or reflection agent (agent module is selectable via `.env`)  
  - Agents can self-loop, collaborate, reflect, or select roles as coded in agent modules  
- **Session-based chat** with persistable conversation history  
- **FastAPI backend** with REST endpoints for chat/reset/history  
- **Modern Streamlit web frontend** for real-time chat, session reset, and history viewing  
- **Environment-based configuration** via `.env`  
