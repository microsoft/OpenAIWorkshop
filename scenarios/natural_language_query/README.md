# Overview
This application demonstrates the of Open AI (ChatGPT/GPT-4) to help answer business questions by performing advanced data analytic tasks on a business database.
Examples of questions are:
- Simple: Show me daily revenue trends in 2016  per region
- More difficult: Is that true that top 20% customers generate 80% revenue in 2016?
- Advanced: Forecast monthly revenue for next 12 months starting from June-2018

The application supports Python's built-in SQLITE .
# Installation 
## Azure Open AI setup
1. Create an Azure OpenAI deployment in an Azure subscription with a GPT-35-Turbo deployment and preferably a GPT-4 deployment.
Here we provide options to use both but GPT-4 should be used to address difficult & vague  questions.
We assume that your GPT-4 and CHATGPT deployments are in the same Azure Open AI resource.
## [Create Azure AI Search Service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal)

## Install the application locally 
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/natural_language_query```
2. Provide settings for Open AI and Database.You can either create a `secrets.env` file in the root of this folder (scenarios/incubations/automating_analytics) as below or do it using the app's UI later on. 
    - use built-in SQLITE.
        ```txt
        AZURE_OPENAI_ENDPOINT="https://YOUR_OPENAI.openai.azure.com/"
        AZURE_OPENAI_API_KEY=""
        AZURE_OPENAI_EMB_DEPLOYMENT="text-embedding-ada-002"
        AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4-1106"
        AZURE_OPEN_AI_VISION_DEPLOYMENT=gpt-4-vision
        AZURE_SEARCH_SERVICE_ENDPOINT="https://.search.windows.net"
        AZURE_SEARCH_INDEX_NAME=sql_query_caches #name of the Azure search index that cache the SQL query
        AZURE_SEARCH_ADMIN_KEY=
        USE_SEMANTIC_CACHE=True

        ```
4. Create a python environment with version from 3.8 and 3.10
    - [Python 3+](https://www.python.org/downloads/)
        - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
        - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`. 
5. Import the requirements.txt `pip install -r requirements.txt`
6. Run the ```python create_cache_index.py``` to create index for the SQL query cache
7. To run the application from the command line: `streamlit run copilot.py`
8. If you are a Mac user, please follow [this](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos?view=sql-server-ver16) to install ODBC for PYODBC
## Deploy the application to Azure 
This application can be deployed to an Azure subscription using the Azure Developer CLI. 
There is no need to have any coding experience to deploy this application but you will need permissions to create resources in an Azure Subscription
To deploy to Azure:
- Install [Azure Developer CLI](https://aka.ms/azure-dev/install)   
- Use either `git clone https://github.com/microsoft/OpenAIWorkshop.git` to clone the repo or download a zip
- Go to the local directory of the OpenAIWorkshop
    > 💡 NOTE: It is very important to be in the root folder of the project
- Authenticate to Azure by running `azd auth login`
- Create a local environment `azd env new`
    > 💡 NOTE: If deploying to the same Subscription as others, use a unique name
- Deploy the app and infrastructure using `azd up`




