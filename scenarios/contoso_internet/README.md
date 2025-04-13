## Business Scenario Description    
"Contoso Communications" provides telecom and internet services. Customers frequently submit requests about billing, account management, service status, and promotions. Requests range from simple queries (single data source) to complex questions requiring multiple backend systems interactions.  
  
---  


## Backend System Setup & Details    
  
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
  
## Agentic System Design    
  
Participants will implement and use an agentic AI system with the following components:  
  
### Single-Agent Setup (Simple & Medium Complexity Scenarios)  
  
**Primary Agent (Generalist)**    
- **Role:** Handles end-to-end requests independently.    
- **Operations:**    
  - Analyzes and understands customer requests.    
  - Queries backend systems (CRM, Billing, Promotions).    
  - Retrieves relevant documents from the knowledge base.    
  - Synthesizes information and formulates customer responses.  
  
**Memory Implementation:**    
- Short-term memory: Maintains session context during interaction.    
- Simple caching: Stores recent data lookups for faster subsequent access.  
  
---  
  
### Multi-Agent Setup (Complex Scenarios)  
  
In complex scenarios, participants will implement a coordinated multi-agent architecture as follows:  
  
| Agent Type | Role & Responsibility | Operations |  
|------------|-----------------------|------------|  
| **Analysis & Planning Agent** | Central coordinator responsible for interpreting customer requests, planning actions, delegating tasks to specialized agents, and integrating results. | - Parses and analyzes abstract customer requests.<br>- Creates and dynamically updates task plans.<br>- Orchestrates communication between specialized agents.<br>- Integrates findings and prepares final responses. |  
| **Structured Data Lookup Agent** | Specialized agent responsible for structured backend queries. | - Executes structured data queries (CRM, Billing, Promotions, Security systems).<br>- Returns structured results to Analysis & Planning agent. |  
| **Knowledge Base Search Agent** | Specialized agent managing knowledge-base interactions. | - Performs semantic searches in knowledge base.<br>- Retrieves relevant policy documents, troubleshooting guides, and procedures.<br>- Returns summarized or relevant extracts to Analysis & Planning agent. |  
| **Communication & Response Agent** | Specialized agent responsible for crafting and delivering customer responses clearly and effectively. | - Generates natural language response from integrated data.<br>- Manages dialogue context, ensuring clarity and coherence. |  
  
---  
  
### Memory Implementation in Multi-Agent Setup  
  
**Individual Agent Memory:**    
- Short-term conversational context storage (session memory).    
- Structured data lookup cache for faster retrieval.    
- Semantic search memory for knowledge base queries.  
  
**Shared Context Memory:**    
- Centralized, shared memory system that facilitates context sharing and coordination between multiple agents.    
- Stores intermediate task plans, status updates, and inter-agent communication.    
- Implementable via vector-database-based memories or shared in-memory data structures.  




### Customer Request Examples  
  
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
  
