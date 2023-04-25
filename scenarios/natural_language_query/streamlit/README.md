# Overview
This application demonstrates the of Open AI (ChatGPT/GPT-4) to help answer business questions by performing advanced data analytic tasks on a business database.
Examples of questions are:
- Simple: Show me daily revenue trends in 2016  per region
- More difficult: Is that true that top 20% customers generate 80% revenue in 2016?
- Advanced: Predict monthly revenue for next 12 months starting from June-2018
The application supports Python's built-in SQLITE as well as your own Microsoft SQL Server.
# Minimum Installation
In order to run this locally or deploy to your Azure Subscription, you will need to do the following:

1. Create an Azure OpenAI deployment in an Azure subscription with a GPT-35-Turbo deployment and preferably a GPT-4 deployment.
Here we provide options to use both but GPT-4 should be used to address difficult & vague  questions.
We assume that your GPT-4 and CHATGPT deployments are in the same Azure Open AI resource.
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download via zip). 

## To Run Locally
- [Azure Developer CLI](https://aka.ms/azure-dev/install)
- [Python 3+](https://www.python.org/downloads/)
    - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
    - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`.    

>NOTE: Your Azure Account must have `Microsoft.Authorization/roleAssignments/write` permissions, such as [User Access Administrator](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#user-access-administrator) or [Owner](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#owner).  


# Running Locally
1. Navigate to ```cd scenarios/natural_language_query/streamlit```
1. Create a python environment with version from 3.7 and 3.10
1. Import the requirements.txt `pip install -r requirements.txt`
1. To run the application from the command line: `streamlit run app.py`
1. The UI prompts for settings. If you want to save these so the next time you run the project you don't have to type them in, you can create a `secrets.env` file in the root of streamlit folder
    - Option 1: use built-in SQLITE. Then you don't need to install SQL Server.
        ```txt
        AZURE_OPENAI_API_KEY="9999999999999999999999999"
        AZURE_OPENAI_GPT4_DEPLOYMENT="NAME_OF_GPT_4_DEPLOYMENT"
        AZURE_OPENAI_CHATGPT_DEPLOYMENT="NAME_OF_CHATGPT_4_DEPLOYMENT"
        AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
        SQL_ENGINE = "sqlite"
        ```
    - Option 2: use your own SQL Server

        ```txt
        AZURE_OPENAI_API_KEY="9999999999999999999999999"
        AZURE_OPENAI_ENDPOINT="https://openairesourcename.openai.azure.com/"
        AZURE_OPENAI_GPT4_DEPLOYMENT="NAME_OF_GPT_4_DEPLOYMENT"
        AZURE_OPENAI_CHATGPT_DEPLOYMENT="NAME_OF_CHATGPT_4_DEPLOYMENT"
        SQL_USER="sqluserid"
        SQL_PASSWORD="sqlpassword"
        SQL_DATABASE="WideWorldImportersDW"
        SQL_SERVER="sqlservername.database.windows.net"
        ```
7. If you are a Mac user, please follow [this](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos?view=sql-server-ver16) to install ODBC for PYODBC
# Upload to use in Azure App Service
This application can be deployed to an Azure subscription using the Azure Developer CLI. There is no need to have any coding experience to deploy this application but you will need permissions to create resources in an Azure Subscription

To deploy to Azure:
- Install [Azure Developer CLI](https://aka.ms/azure-dev/install)
- Use either `git clone https://github.com/microsoft/OpenAIWorkshop.git` to clone the repo or download a zip
- Go to the local directory of the OpenAIWorkshop
- Authenticate to Azure by running `azd auth login`
- Create a local environment `azd env new`
    > 💡 NOTE: If deploying to the same Subscription as others, use a unique name
- Deploy the app and infrastructure using `azd up`

# How to use the applications

After you run the run the application, go to website and you'll see UI like this.
<img width="1159" alt="image" src="../../../documents/media/da_assistant1.png">
If you did not maintain secrets values above, you will need to provide that in settings. Here, please provide Open AI keys, deployment name and URL for ChatGPT. Optionally, you can provide the information for GPT-4 for advanced questions. If you don't provide information for GPT-4, the engine will by default use ChatGPT.
For data, you can use the built-in SQLITE demo dataset or you can choose to specify your own SQL Server. 