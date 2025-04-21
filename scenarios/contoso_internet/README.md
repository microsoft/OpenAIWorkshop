
## Goal
This project focuses on revamping the existing OpenAI workshop content, aligning it with the latest Agentic AI technologies. The primary objective is to deliver an updated curriculum that equips participants with the skills to design and implement agent-based AI systems using cutting-edge tools like Azure Agent Service, Semantic Kernel, and Autogen frameworks. The refreshed content aims to guide learners through practical applications, enabling them to automate customer requests through structured data queries and knowledge base searches, and to advance from simple single-agent setups to complex multi-agent architectures.

## 1. Business Scenario Description  
  
"Contoso Communications" provides telecom and internet services. Customers frequently submit requests about billing, account management, service status, and promotions. Requests range from simple queries (single data source) to complex questions requiring multiple backend systems interactions.  
  
---  
  
## 2. Backend System Setup & Details  
  
Participants will use the following simulated backend systems during the workshop. These systems replicate real-world business environments and will be accessible via structured APIs or simplified interfaces.  
  
| System Name | Description | Data Types | Interaction |  
|-------------|-------------|------------|-------------|  
| **CRM System (e.g., Salesforce or Dynamics CRM)** | Central repository for customer profiles, subscriptions, contract details, and interaction history. | Customer account data, subscription plans, contract dates, customer identification data. | Structured API queries (REST API). |  
| **Billing Database** | System containing structured invoice and subscription data. | Invoice amounts, billing history, plan details, payment status. | Structured SQL-style queries or REST API. |  
| **Product and Promotion Database** | Contains structured data about available products, upgrades, promotions, discounts, and eligibility criteria. | Promotion details, eligibility criteria, product/service details. | Structured API queries (REST API). |  
| **Security & Authentication Database** | Manages structured information about account security status, login attempts, and authentication issues. | Account lockout reasons, authentication logs, security flags. | Structured API queries or REST API. |  
| **Knowledge Base (Confluence or SharePoint-like system)** | Centralized repository for documentation, FAQs, troubleshooting guides, internal policies, and procedural guidelines. | Unstructured/semi-structured text documents, policy documents, troubleshooting procedures. | Semantic search API, keyword-based or embedding-based retrieval. |  
  
**Note:** Participants will be provided with simplified API endpoints and credentials to interact with these backend systems directly during the hands-on exercises.  
  
---  
  
## 3. Model Context Protocol API Service Endpoints  
  
**The following services are exposed as tools for AI Agents:**  
  
- `get_all_customers`: List all customers with basic info.  
- `get_customer_detail`: Get a full customer profile including their subscriptions.  
- `get_subscription_detail`: Detailed subscription view including invoices (with payments) and service incidents.  
- `get_invoice_payments`: Return invoice-level payments list.  
- `pay_invoice`: Record a payment for a given invoice and get new outstanding balance.  
- `get_data_usage`: Daily data-usage records for a subscription over a date range (optional aggregation).  
- `get_promotions`: List every active promotion (no filtering).  
- `get_eligible_promotions`: Promotions eligible for a given customer (evaluates basic loyalty/date criteria).  
- `search_knowledge_base`: Semantic search on policy/procedure knowledge documents.  
- `get_security_logs`: Security events for a customer (newest first).  
- `get_customer_orders`: All orders placed by a customer.  
- `get_support_tickets`: Retrieve support tickets for a customer (optionally filter by open status).  
- `create_support_ticket`: Create a new support ticket for a customer.  
- `get_products`: List or search available products (optional category filter).  
- `get_product_detail`: Return a single product by ID.  
- `update_subscription`: Update one or more mutable fields on a subscription.  
- `unlock_account`: Unlock a customer account locked for security reasons.  
- `get_billing_summary`: What does a customer currently owe across all subscriptions?  
  
---  
  
## 4. Agent System Design  
  
### Common Agent Design Patterns  
  
- **Intelligent Single Agent:** Single intelligent agent interacting with user and leveraging tools (structured APIs, RAG-based search) to handle user requests.  
- **Multi-domain Agents:** Coordinator agent manages multiple specialist agents, each handling requests within their specific business domain.  
- **Collaborative Multi-Agent System:** Multiple agents coordinated by a planning agent to collaboratively solve complex problems.  
  
#### Special Sub-patterns (can be integrated within any of the above patterns):  
  
- **Coding Agent:** Agent that generates code to address complex computational tasks.  
- **Reflection Pattern:** Agents capable of self-reflection before responding or leveraging separate reviewer/advisor agents for feedback in multi-agent configurations.  
  
---  
  
### Agent Setup  
  
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
  
#### 🧩 Multi-Domain Agent Setup  
  
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
  
#### 🧩 Collaborative Multi-Agent System Setup  
  
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
  
## 5. Customer Request Examples  
  
---  
  
#### Example 1:   
  
**Customer:** "I noticed my last invoice was higher than usual—can you help me understand why and what can be done about it?"    
  
**Analysis & Plan:**    
- Check billing history and recent changes in subscriptions or charges.    
- Review policy for invoice adjustments.    
  
**Systems Accessed:**    
- CRM, Billing Database, Knowledge Base.    
  
---  
  
#### Example 2:   
  
**Customer:** "My internet service seems slower than before—can you check what's happening?"    
  
**Analysis & Plan:**    
- Review the customer’s current subscription plan and service status.    
- Check for recent service incidents or network usage history.    
- Search knowledge base for troubleshooting guidance or policies on service quality guarantees.    
  
**Systems Accessed:**    
- CRM (Customer Profile).    
- Service Monitoring and Diagnostics System (Technical Data).    
- Knowledge Base (Troubleshooting Guides).    
  
---  
  
#### Example 3:   
  
**Customer:** "I'm traveling abroad next month. What should I do about my phone plan?"    
  
**Analysis & Plan:**    
- Check the customer’s current mobile subscription, roaming capabilities, and international charges.    
- Search knowledge base for suitable international roaming options or temporary international plans.    
- Update the plan after verifying eligibility and availability.    
  
**Systems Accessed:**    
- CRM (Current Subscription).    
- Product & Service Database (Available Plans).    
- Knowledge Base (International Roaming Policies).    
  
---  
  
#### Example 4:   
  
**Customer:** "I tried logging into my account, but it says I'm locked out. Can you help?"    
  
**Analysis & Plan:**    
- Review the customer’s account status, recent login attempts, and security alerts.    
- Investigate reasons for account lockout in the security database.    
- Search knowledge base for account security policies, unlock procedures, and verification processes.    
  
**Systems Accessed:**    
- CRM (Customer Account).    
- Security & Authentication System (Security Data).    
- Knowledge Base (Unlock Procedures, Security Policies).    
  
---  
  
#### Example 5:   
  
**Customer:** "Do I qualify for any discounts or promotions right now?"    
  
**Analysis & Plan:**    
- Check the customer’s account history, current subscriptions, loyalty status, and previous promotional usage.    
- Search the product database for active promotions or discounts applicable to the customer’s profile.    
- Refer to the knowledge base for eligibility criteria for promotions or loyalty rewards.    
  
**Systems Accessed:**    
- CRM (Customer Profile, Loyalty Information).    
- Promotions & Discounts Database (Promotional Data).    
- Knowledge Base (Promotion Eligibility Policies).    
  
---  
  
#### Example 6:   
  
**Customer:** "I want to return a product I recently purchased. What's the process?"    
  
**Analysis & Plan:**    
- Confirm recent purchases from the customer’s order history.    
- Check eligibility for return based on purchase date and item category.    
- Search the knowledge base for return policies, guidelines, and procedures.    
  
**Systems Accessed:**    
- CRM & Order Management System (Order/Purchase Data).    
- Knowledge Base (Return Policies and Guidelines).    
  
---  
  
### [Checkout the challenges document for more scenarios](backend_services/data/customer_scenarios.md)  