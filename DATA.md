# Data

### 1. Data Generation ([agentic_ai/backend_services/data)](agentic_ai/backend_services/data))  
  
- **create_db.py**    
  Generates the entire customer, subscription, billing, and usage database (`contoso.db`) with:  
    - 250 randomized customers  
    - 9 deterministic “AI challenge” scenarios  
    - Linked tables for payments, promotions, support, incidents, etc.  
    - Scenario answer keys written out to `customer_scenarios.md`  
    - Optionally creates knowledge document embeddings if Azure OpenAI is configured  
  
- **contoso.db**    
  The generated SQLite database (run `python data/create_db.py` to generate).  
  
- **SCENARIOS.md**    
  All nine "challenge" scenarios (e.g. “invoice anomaly”, “promotion eligibility”), each with:  
  - Customer context  
  - Challenge prompt  
  - Detailed solution (“answer-key” for agents)  
  
- **kb.json**    
  Knowledge base entries used for agent tool lookups, including policies, procedures, troubleshooting guides, etc.  
  
---  
 