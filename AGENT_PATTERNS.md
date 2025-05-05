
![alt text](image-1.png)
# Microsoft AI Agentic Workshop Agent Design Patterns 
  
This document describes the different Agent Design Patterns for AI Agentic Workshop from Microsoft. 
This is architectural information that can be used by users for their Agent designs
  
## 1. Agent System Design  
  
### Common Agent Design Patterns  
  
- **Intelligent Single Agent:** Single intelligent agent interacting with user and leveraging tools (structured APIs, RAG-based search) to handle user requests.  
- **Multi-domain Agents:** Coordinator agent manages multiple specialist agents, each handling requests within their specific business domain.  
- **Collaborative Multi-Agent System:** Multiple agents coordinated by a planning agent to collaboratively solve complex problems.  
  
#### Special Sub-patterns (can be integrated within any of the above patterns):  
  
- **Coding Agent:** Agent that generates code to address complex computational tasks.  
- **Reflection Pattern:** Agents capable of self-reflection before responding or leveraging separate reviewer/advisor agents for feedback in multi-agent configurations.  
  
---  
  
### 2. Agent Setup  
  
#### 🧩 Intelligent Single Agent Setup  
  
**Primary Agent**  
- **Role:** Handles end-to-end requests using multiple tools.  
- **Operations:**  
    - Analyzes and understands customer requests.  
    - Queries backend systems (CRM, Billing, Promotions).  
    - Retrieves relevant documents from the knowledge base.  
    - Synthesizes information and formulates customer responses.  
  
**Memory Implementation:**  
- Short-term memory: Maintains session context during interaction.  
  
---  
  
#### 3. 🧩 Multi-Domain Agent Setup  
  
In this simplified multi-domain architecture, the Coordinator Agent's primary responsibility is lightweight domain detection and routing. It does not engage in complex planning or orchestration. Instead, it directly forwards user requests to appropriate domain-specialist agents who independently handle the interaction with the user within their own specialized domain. Once the user's request moves beyond a specialist agent's domain, the request is returned to the Coordinator Agent for further routing.  
  
**Agent Roles & Responsibilities:**  
  
1. **Coordinator Agent (Router)**  
    - **Role:** Acts purely as a lightweight dispatcher, quickly identifying the correct domain specialist based on initial customer request analysis and routing the request accordingly.  
    - **Operations:**  
        - Analyzes the user's initial request to determine the relevant domain.  
        - Routes the request to the appropriate specialist agent.  
        - Receives requests back from specialist agents once their domain tasks are complete or if the user moves to another domain.  
    - **Memory & Context:** Minimal context storage (only maintains domain routing logic and basic conversational state).  
  
2. **Specialist Agents (Independent Domain Experts)**  
    - **Role:** Directly interact with users within their specialized domains, independently managing all communication, analysis, planning, queries, and responses.  
    - **Operations:**  
        - Independently handle requests within their domain without involving other specialist agents.  
        - Perform structured API queries or knowledge base retrieval as needed within their domain.  
        - Maintain short-term memory for conversational context within their domain.  
        - Hand-off back to Coordinator Agent if the user's request shifts to another domain.  
    - **Specialist agents include:**  
        - **CRM & Billing Agent:** Handles structured queries related to customer profile data, account details, billing information, invoices, subscriptions, and payment status.  
        - **Product & Promotions Agent:** Manages structured queries related to products, promotions, discounts, eligibility criteria, and available subscription plans.  
        - **Security & Authentication Agent:** Specializes in account security, authentication issues, login attempt analysis, and account lockout resolution.  
  
---  
  
#### 4. 🧩 Collaborative Multi-Agent System Setup  
  
In complex scenarios, participants will implement a collaborative multi-agent architecture. Each agent specializes in a specific functional domain and collaboratively addresses more sophisticated customer requests. A central **Analysis & Planning Agent** orchestrates interactions, task delegation, and integrates results from various domain specialists.  
  
Critically, **all functional specialist agents** independently utilize the organization's centralized **Knowledge Base** proactively. They retrieve semi-structured and unstructured content such as FAQs, internal policies, troubleshooting protocols, guidelines, and best practices. Leveraging Knowledge Base resources ensures that every agent consistently adheres to organizational standards and formulates accurate, informed, and comprehensive responses within their specialized domain areas.  
  
**Agent Roles & Responsibilities:**  
  
| Agent | Role Description | Operations | Knowledge Base Usage |  
|-------|------------------|------------|----------------------|  
| **Analysis & Planning Agent** | Central orchestrator responsible for parsing abstract customer requests, decomposing these into clear subtasks, delegating subtasks to specific specialists, and synthesizing agent outputs into unified customer responses. | - Parses/analyzes abstract customer requests <br> - Identifies required subtasks <br> - Delegates tasks clearly to respective domain agents <br> - Dynamically revises task plans based on specialist agents' inputs <br> - Integrates all agents' outputs into final cohesive responses | Primarily relies on information synthesized from specialist agents; direct Knowledge Base access is minimal and situational. |  
| **CRM & Billing Agent** (Functional Specialist)| Handles structured queries around customer profiles, subscriptions details, invoicing, billing histories, and payment processing. | - Queries CRM & Billing backend databases for structured data <br> - Provides account status, billing history, subscription details, and billing-related information <br> - Shares relevant data/results with Analysis & Planning Agent and other specialists as necessary | Frequently consults Knowledge Base materials related to billing policies, account-handling protocols, and payment processing procedures to inform and validate structured-query responses. |  
| **Product & Promotions Agent** (Functional Specialist) | Manages structured information concerning promotions, products, eligibility, customer upgrades, and discounts. | - Queries structured data from Product & Promotions backend systems <br> - Determines product availability, promotions, discounts, and customer eligibility <br> - Provides structured product/promotional information and recommendations to Analysis & Planning Agent and potentially other specialists | Regularly accesses Knowledge Base content to retrieve promotional terms, eligibility guidelines, product/service-related FAQs and internal documentation to enhance structured responses and recommendations. |  
| **Security & Authentication Agent** (Functional Specialist) | Handles customer authentication queries, security issues, account lockouts, and reviews login attempts. | - Queries backend structured data (security logs, login history/authentication events) from Security & Authentication databases <br> - Analyzes security statuses/issues, authentication logs, and provides recommended actions <br> - Shares security assessments and recommendations with Analysis & Planning Agent and other agents as needed | Consistently leverages Knowledge Base documentation such as security policies, authentication guidelines, lockout troubleshooting protocols, and best practices to ensure accurate, compliant, and informed security-focused responses. |  
  
---  
  
### Memory Implementation in Multi-Agent Setup  
  
- **Individual Agent Memory:**  
    - Short-term conversational context storage (session memory).  
    - Semantic search memory for knowledge base queries.  
  
- **Shared Context Memory:**  
    - Centralized, shared memory system that facilitates context sharing and coordination between multiple agents.  
    - Stores intermediate task plans, status updates, and inter-agent communication.  
    - Implementable via vector-database-based memories or shared in-memory data structures.  
  
---  