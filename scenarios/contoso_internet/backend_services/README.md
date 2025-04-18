# Contoso Backend Services  
  
This repository provides a complete backend for the Contoso AI agent use case, simulating a realistic customer, subscription, and knowledge base environment. It contains tools to generate a synthetic SQLite database with customer scenarios, and exposes a typed API (via FastMCP) consumable by AI agent frameworks.  
  
---  
  
  
## Major Components  
  
### 1. Data Generation (`data/`)  
  
- **create_db.py**    
  Generates the entire customer, subscription, billing, and usage database (`contoso.db`) with:  
    - 250 randomized customers  
    - 9 deterministic “AI challenge” scenarios  
    - Linked tables for payments, promotions, support, incidents, etc.  
    - Scenario answer keys written out to `customer_scenarios.md`  
    - Optionally creates knowledge document embeddings if Azure OpenAI is configured  
  
- **contoso.db**    
  The generated SQLite database (run `python data/create_db.py` to generate).  
  
- **customer_scenarios.md**    
  All nine "challenge" scenarios (e.g. “invoice anomaly”, “promotion eligibility”), each with:  
  - Customer context  
  - Challenge prompt  
  - Detailed solution (“answer-key” for agents)  
  
- **kb.json**    
  Knowledge base entries used for agent tool lookups, including policies, procedures, troubleshooting guides, etc.  
  
---  
  
### 2. Backend API Service (`mcp_service.py`)  
  
A robust Model Context Protocol (MCP) API for agent integration, providing:  
- Customer/account lookup tools  
- Subscription/invoice/payment history  
- Data usage and support ticket endpoints  
- Semantic knowledge base search (embedding-powered)  
- Promotion eligibility checker  
- Security log viewing/unlock actions  
- (All endpoints are strictly “toolified” for agent consumption, with clear schemas via Pydantic models)  
  
Runs as a FastMCP/asyncio service, exposing endpoints for integration with AI agents—see below for running instructions.  
  
---  
  
### 3. Deployment/Containerization  
  
- **Dockerfile.mcp**    
  Dockerfile optimized for production deployment (Python 3.11, minimal image). Default port exposure is 8000 (change as needed).  
  
- **deploy_mcp.sh**    
  Example Bash script to build, push, and deploy the backend as an Azure Container App, including resource group and registry setup.    
  _Note:_ Update variables inside the script for your resource group, region, etc.  
  
- **.env.sample**    
  Template for local or cloud environment variables (database path, Azure OpenAI config, etc.).    
  _To use:_ Copy to `.env` and fill in secrets as needed.  
  
---  
  
### 4. Configuration  
  
**Environment (.env) variables supported:**  
  
| Variable                          | Purpose                                          | Example Value                                           |  
|------------------------------------|--------------------------------------------------|--------------------------------------------------------|  
| AZURE_OPENAI_ENDPOINT             | Azure OpenAI endpoint                            | `https://YOUR_RESOURCE.openai.azure.com`               |  
| AZURE_OPENAI_API_KEY              | API key for embedding/chat                       | (xxxxxxxxxxxx)                         |  
| AZURE_OPENAI_CHAT_DEPLOYMENT      | Chat deployment name                             | `gpt-4o`                                               |  
| AZURE_OPENAI_API_VERSION          | API version                                      | `2025-03-01-preview`                                   |  
| AZURE_OPENAI_EMBEDDING_DEPLOYMENT | Embedding deployment name                        | `text-embedding-ada-002`                               |  
| DB_PATH                           | SQLite db location (relative to app root)        | `data/contoso.db`                                      |  
  
---  
  
## Quickstart  
  
1. **Generate the Demo Data**    
   (Requires Python 3.11+, install requirements via `pip install -r requirements.txt`)  
  
    ```bash  
    cd data/  
    python create_db.py  
    ```  
  
2. **Review the scenarios:**    
    - See `data/customer_scenarios.md` for all challenge case descriptions & answer keys.  
  
3. **Run the API Locally**  
  
   - Copy `.env.sample` → `.env` and fill in any required values.  
   - Start the service:  
  
    ```bash  
    python mcp_service.py  
    ```  
  
   - The service listens on `0.0.0.0:8000` by default (FastMCP SSE server).  
  
4. **Containerize (optional):**  
    - Build the Docker image:  
  
    ```bash  
    docker build -f Dockerfile.mcp -t mcp-backend .  
    docker run -it -p 8000:8000 --env-file .env mcp-backend  
    ```  
  
5. **Cloud Deployment (Azure Container Apps example):**  
  
    ```bash  
    bash deploy_mcp.sh  
    ```  
    - (Edit `deploy_mcp.sh` to fit your Azure account/resource group/etc.)  
  
---  
  
## Integration: Consuming as Agent Tools  
  
The API is designed for “tool calling” agents (e.g., OpenAI function-calling, Meta Code, etc.), using named tools with strongly-typed arguments and responses. The scenario data provides a broad reasoning playground for LLM evaluation, tool-testing, or troubleshooting assistance.  
  
- **Endpoints are documented via Pydantic schemas in `mcp_service.py`.**  
- **Knowledge base search is semantic, using text embeddings (Azure or zero-vector fallback).**  
  
---  
  
## Extending / Regenerating Data  
  
- Add more deterministic or random scenarios in `data/create_db.py` as needed.  
- Add new knowledge base entries to `data/kb.json`.  
- Rerun `python data/create_db.py` after changes.  
  
---  
  
## License  
  
MIT or similar (set your organization’s actual license here).  
  
---  
  
## Credits  
  
- Synthetic data, structure, and tools © Microsoft/Contoso demo authors.  
- Data generation via [Faker](https://faker.readthedocs.io/), Knowledge search via [Azure OpenAI], API implementation via [FastMCP].  
  