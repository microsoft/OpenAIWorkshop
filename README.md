![alt text](media/image-1.png)
# Microsoft AI Agentic Workshop Repository  
  
Welcome to the official repository for the Microsoft AI Agentic Workshop! This repository provides all the resources, code, and documentation you need to explore, prototype, and compare various agent-based AI solutions using Microsoft's leading AI technologies.  
  
---  
  
## Quick Links  
  
- [Business Scenario and Agent Design](./SCENARIO.md)  
- [Getting Started (Setup Instructions)](./SETUP.md)  
- [System Architecture Overview](./ARCHITECTURE.md)  
- [Data Sets](./DATA.md)  
- [Code of Conduct](./CODE_OF_CONDUCT.md)  
- [Security Guidelines](./SECURITY.md)  
- [Support](./SUPPORT.md)  
- [License](./LICENSE)  
  
---  
  
## What You Can Do With This Workshop  
  
- **Design and prototype agent solutions** for real-world business scenarios.  
- **Compare single-agent vs. multi-agent** architectures and approaches.  
- **Develop and contrast agent implementations** using different platforms:  
  - Azure AI Agent Service  
  - Semantic Kernel  
  - Autogen  
  
---  
  
## Key Features  
  
- **Configurable LLM Backend:** Use the latest Azure OpenAI GPT models (e.g., GPT-4.1, GPT-4o).  
- **MCP Server Integration:** Advanced tools to enhance agent orchestration and capabilities.  
- **A2A (Agent-to-Agent) Protocol Support:** Enables strict cross-domain, black-box multi-agent collaboration using [Google's A2A protocol](https://github.com/google-a2a/A2A).
- **Flexible Agent Architecture:**  
  - Supports single-agent, multi-agent, or reflection-based agents (selectable via `.env`).  
  - Agents can self-loop, collaborate, reflect, or take on dynamic roles as defined in modules.  
- **Session-Based Chat:** Persistent conversation history for each session.  
- **Full-Stack Application:**  
  - FastAPI backend with RESTful endpoints (chat, reset, history, etc.).  
  - Streamlit frontend for real-time chat, session management, and history viewing.  
- **Environment-Based Configuration:** Easily configure the system using `.env` files.  
  
---  
  
## Getting Started  
  
1. Review the [Setup Instructions](./SETUP.md) for environment prerequisites and step-by-step installation.  
2. Explore the [Business Scenario and Agent Design](./SCENARIO.md) to understand the workshop challenge.  
3. Dive into  [System Architecture](./ARCHITECTURE.md) before building and customizing your agent solutions.  
4. Utilize the [Support Guide](./SUPPORT.md) for troubleshooting and assistance.  
  
---  
  
## 🆕 A2A (Agent-to-Agent) Cross-Domain Demo  
  
This repository now supports a strict cross-domain multi-agent scenario using the A2A protocol, enabling message-driven, black-box collaboration between a customer-service agent and a logistics agent.  
  
**A2A Example Included:**    
 See [`agentic_ai/agents/semantic_kernel/multi_agent/a2a`](agentic_ai/agents/semantic_kernel/multi_agent/a2a).  
  
---  

## Contributing  
  
Please review our [Code of Conduct](./CODE_OF_CONDUCT.md) and [Security Guidelines](./SECURITY.md) before contributing.  
  
---  
  
## License  
  
This project is licensed under the terms described in the [LICENSE](./LICENSE) file.  
  
---  