
# Installation 
## Open AI setup
Create an Azure OpenAI deployment in an Azure subscription with a GPT-4-1106  (prefered) or GPT-35-Turbo-1106 deployment
## Run the application locally
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/incubations/copilot/cf_copilot```
2. Create a `secrets.env` file under copilot folder
```
    AZURE_OPENAI_API_KEY="OPEN_AI_KEY"
    AZURE_OPENAI_ENDPOINT="https://YOUR_OPEN_AI_SERVICE.openai.azure.com/"
    AZURE_OPENAI_CHAT_DEPLOYMENT #name of your Open AI Chat Deployment
    CF_API_KEY=#api key for confluent governance API
    CF_API_SECRET=Confluent secret
    CF_GRAPHQL_ENDPOINT=#CF graphql endpoint (e.g.https://d-q2n1d.westus2.azure.confluent.cloud/catalog/graphql)
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








