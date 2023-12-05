
# Installation 
## Open AI setup
Create an Azure OpenAI deployment in an Azure subscription with a GPT-4-1106 deployment and a ada-text-embedding-002 deloyment
## Run the application locally
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/incubations/copilot/cf_copilot```
2. Create a `secrets.env` file under copilot folder
```
    AZURE_OPENAI_API_KEY="OPEN_AI_KEY"
    AZURE_OPENAI_ENDPOINT="https://YOUR_OPEN_AI_SERVICE.openai.azure.com/"
    AZURE_OPENAI_EMB_DEPLOYMENT #name of your embedding model deployment
    AZURE_OPENAI_CHAT_DEPLOYMENT #name of your Open AI Chat Deployment
    USE_AZCS="False" #if false, it will use the Faiss library for search
    AZURE_SEARCH_SERVICE_ENDPOINT="https://YOUR_SEARCH_SERVICE.search.windows.net"
    AZURE_SEARCH_INDEX_NAME=YOUR_SEARCH_INDEX_NAME
    CACHE_INDEX_NAME="YOUR_SEARCH_INDEX_NAME" #optional, required when USE_SEMANTIC_CACHE="True"
    AZURE_SEARCH_ADMIN_KEY=YOUR_SEARCH_INDEX_NAME_KEY
    AZURE_OPENAI_API_VERSION="2023-07-01-preview"
    USE_SEMANTIC_CACHE="False" #set to True if use semantic Cache.
    SEMANTIC_HIT_THRESHOLD=0.9 #Threshold in similarity score to determine if sematic cached will be used
    CF_API_KEY=#api key for confluent governance API
    CF_API_SECRET=Confluent secret
    CF_GRAPHQL_ENDPOINT=#CF graphql endpoint
    BING_SUBSCRIPTION_KEY=Azure Bing's subscription key
    BING_SEARCH_URL=https://api.bing.microsoft.com/v7.0/search

```
3. Create a python environment with version from 3.7 and 3.10

    - [Python 3+](https://www.python.org/downloads/)
        - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
        - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`. 
4. Import the requirements.txt `pip install -r requirements.txt`
5. To run the  copilot from the command line: `streamlit run copilot.py`

## Deploy the application to Azure 
Review and customize the bicep template under https://github.com/microsoft/OpenAIWorkshop/tree/main/infra and use azd to deploy to Azure








