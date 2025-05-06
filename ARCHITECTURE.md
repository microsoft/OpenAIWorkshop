

# System Architecture  
![System Architecture Diagram](media/system_architecture.png)
  
This document outlines the architecture for the Microsoft AI Agentic Workshop platform. The architecture is modular and designed to support a wide variety of agent design patterns, allowing you to focus on agent implementation and experimentation without changing the core infrastructure.  
  
---  
  
## High-Level Overview  
  
The system comprises **four primary layers**:  
  
1. **Front End**: User-facing chat interface.  
2. **Backend**: Orchestrates conversation flow, session state, and acts as a bridge between the front end and agent logic.  
3. **Agent Service Layer**: Loads, instantiates, and operates agent implementations (e.g., single-agent, multi-agent, multi-domain patterns).  
4. **Model Context Protocol (MCP) API Server**: Exposes structured business operations and tools via API endpoints for agent use.  
  
Supporting databases include:  
  
- **SQL Database**: Contains core business/transactional data (customers, subscriptions, invoices, etc.).  
- **Vector Database**: Enables semantic (embedding-based) retrieval over internal knowledge/documents.  
  
---  
  
## Component Breakdown  
  
### 1. Frontend  
  
- **Technology**: Streamlit (Python)  
- **Functionality**:  
  - Presents an interactive chat interface.  
  - Maintains a unique, persistent session for each user.  
  - Displays real-time chat history.  
  - Communicates with the backend using HTTP endpoints for prompt submission, response retrieval, and session management (reset/new conversations).  
  
### 2. Backend  
  
- **Technology**: FastAPI (asynchronous Python)  
- **Responsibilities**:  
  - Exposes HTTP API endpoints for frontend communication.  
  - Manages sessions and conversation history in memory.  
  - Connects inbound user requests with the appropriate agent instance in the Agent Service layer.  
  - Forwards tool/API calls requested by agents to the MCP API server.  
- **Endpoints**:  
  - `/chat`: Processes chat requests and returns agent responses.  
  - `/reset_session`: Clears session memory and context state.  
  - `/history/{session_id}`: Fetches conversation history.  
- **Session Store**: Tracks session state and chat history (in-memory; pluggable for persistent storage).  
  
### 3. Agent Service Layer  
  
- **Design**: Pluggable and modular—enables selecting and loading different agent design patterns:  
  - **Intelligent Single Agent**: One agent using tools to handle requests end-to-end.  
  - **Multi-Domain Agent**: Coordinator agent routes requests to specialist agents (e.g., CRM, Billing, Security).  
  - **Collaborative Multi-Agent System**: Planning/analysis agent orchestrates multiple domain experts.  
- **Capabilities**:  
  - Tool usage via structured API calls to MCP endpoints.  
  - Augmented responses using Retrieval-Augmented Generation (RAG) with the vector knowledge base.  
  - Maintains both short-term (session) and, optionally, shared or long-term memory for multi-step reasoning.  
- **Implementation**:  
  - Built using Semantic Kernel, autogen, or Azure Agent-Service frameworks for agent planning, orchestration, and tool connectivity.  
  - Easily configured and swapped by changing agent module imports and startup parameters.  
  
### 4. Model Context Protocol (MCP) API Server  
  
- **Technology**: FastAPI/asyncio, JSON schema validation with Pydantic.  
- **Purpose**: Simulates realistic enterprise APIs, exposing business and operational data through agent-friendly, structured APIs.  
- **Key Endpoint Categories**:  
  - Customer/account lookup  
  - Subscription, invoice, and payment management  
  - Data usage reporting  
  - Product and promotion queries  
  - Support ticket management  
  - Security log review and account unlock  
  - Semantic search over the knowledge base  
- **Endpoint Examples**:  
  - `get_all_customers`, `get_customer_detail`  
  - `get_subscription_detail`, `get_invoice_payments`, `pay_invoice`  
  - `get_data_usage`, `get_promotions`, `get_eligible_promotions`  
  - `search_knowledge_base`  
  - `get_security_logs`, `unlock_account`  
  - `get_customer_orders`, `get_support_tickets`, `create_support_ticket`  
  - `get_products`, `get_product_detail`, `update_subscription`  
  - `get_billing_summary`  
- **Characteristics**:  
  - Pydantic-model-validated requests and responses for reliable tool invocation.  
  - Serves as the central integration point for all structured data and knowledge base access.  
  
---  
  
## Databases  
  
- **SQL Database**: Stores structured business data, such as customer profiles, subscriptions, invoices, and order histories.  
- **Vector Database**: Stores embedding-based representations of knowledge documents and internal policies, enabling fast and relevant retrieval during RAG operations by agents.  
  
---  
  
## Summary  
  
This four-layer architecture ensures clear separation of concerns across user interaction, backend orchestration, agent intelligence, and enterprise data access. The platform makes it easy to experiment with a wide range of agent frameworks and design patterns, supporting robust, enterprise-grade agentic solutions without the need to modify underlying infrastructure.  