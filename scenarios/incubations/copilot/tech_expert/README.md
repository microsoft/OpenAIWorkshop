# Scenario Overview
This scenario demonstrate the use Azure Open AI's function calling,   hybrid search + semantic reranker in Azure Cognitive Search and Semantic Caching for RAG pattern of complex technical document.
Check out the ```../data/dataprep``` for the script to preprocess PDF documents using Azure Form recognizer with logic to process table data and populate meta data to Azure Cognitive Search Index.

The copilot in this example interact with users to help answer technical questions about products. 
A user has a user profile with products that they have access to.
A small example business flow is implemented in this example which is to clarify which product(s) the question is about with user in case it's not clear.
Then function calling is demonstrated that the copilot will formulate a search query for Azure Cognitive Search and the filtering condition to narrow down the scope of the search (products).


# Installation 
## Open AI setup
Create an Azure OpenAI deployment in an Azure subscription with a GPT-4-0603 deployment and a ada-text-embedding-002 deloyment
## Run the application locally
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/incubations/copilot/tech_expert```
2. Create a `secrets.env` file under ``tech_expert`` folder
```
AZURE_OPENAI_ENDPOINT="/"
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_EMB_DEPLOYMENT="t"
AZURE_OPENAI_CHAT_DEPLOYMENT=""
USE_AZCS="True"
AZURE_SEARCH_SERVICE_ENDPOINT=""
AZURE_SEARCH_INDEX_NAME=
AZURE_SEARCH_ADMIN_KEY=
AZURE_OPENAI_API_VERSION="2023-07-01-preview"
USE_SEMANTIC_CACHE="False" #Set to True for semantic caching.
SEMANTIC_HIT_THRESHOLD=0.9


```
3. Create a python environment with version from 3.7 and 3.10

    - [Python 3+](https://www.python.org/downloads/)
        - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
        - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`. 
4. Import the requirements.txt `pip install -r requirements.txt`
5. To run the multi-agent copilot from the command line: `streamlit run tech_copilot.py`

## Deploy the application to Azure 
##To be added







