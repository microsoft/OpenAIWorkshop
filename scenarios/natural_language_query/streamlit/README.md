# Instructions
1. Create an Azure OpenAI deployment in an Azure subscription with a GPT-35-Turbo deployment and preferably a GPT-4 deployment.
2. Create a `secrets.env` file in the root of this folder
    Option 1: use built-in SQLITE. Then you don't need to install SQL Server.
        ```txt
        AZURE_OPENAI_API_KEY=9999999999999999999999999
        AZURE_OPENAI_DEPLOYMENT_MASTER_NAME="gpt-4"
        AZURE_OPENAI_DEPLOYMENT_TOOL_NAME="gpt-35-turbo"
        AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
        SQLITE_DB_PATH = "../data/northwind.db"
        SQL_ENGINE = "sqlite"
        ```
    Option 2: use SQL Server

        ```txt
        AZURE_OPENAI_API_KEY=9999999999999999999999999
        AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
        AZURE_OPENAI_DEPLOYMENT_MASTER_NAME="gpt-4"
        AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
        SQL_USER=sqluserid
        SQL_PASSWORD=sqlpassword
        SQL_DATABASE=WideWorldImportersDW
        SQL_SERVER=sqlservername.database.windows.net
        ```
3. Create a python environment
4. Import the requirements.txt `pip install -r requirements.txt`
5. From the window, run `streamlit run viz_v2.py`