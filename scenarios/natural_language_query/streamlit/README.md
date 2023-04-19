# Overview
This application demonstrate the of Open AI (ChatGPT/GPT-4) to help answer business questions by performing advanced data analytic tasks on a business database.
Examples of questions are:
- Simple:Show me daily revenue trends in 2016  per region
- More difficult: Is that true that top 20% customers generate 80% revenue in 2016?
- Advanced: Predict monthly revenue for next 12 months starting from June-2018
The application support Python's built-in SQLITE as well as Microsoft SQL Server.
# Instructions
1. Create an Azure OpenAI deployment in an Azure subscription with a GPT-35-Turbo deployment and preferably a GPT-4 deployment.
Here we provide options to use both but GPT-4 should be used to address difficult & vague  questions.
We assume that your GPT-4 and CHATGPT deployments are in the same Azure Open AI resource.
2. Create a `secrets.env` file in the root of this folder

    - Option 1: use built-in SQLITE. Then you don't need to install SQL Server.
        ```txt
        AZURE_OPENAI_API_KEY=9999999999999999999999999
        AZURE_OPENAI_GPT4_DEPLOYMENT="gpt-4"
        AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-35-turbo
        AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
        SQLITE_DB_PATH = "../data/northwind.db"
        SQL_ENGINE = "sqlite"
        ```
    - Option 2: use SQL Server

        ```txt
        AZURE_OPENAI_API_KEY=9999999999999999999999999
        AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
        AZURE_OPENAI_GPT4_DEPLOYMENT="gpt-4"
        AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-35-turbo
        SQL_USER=sqluserid
        SQL_PASSWORD=sqlpassword
        SQL_DATABASE=WideWorldImportersDW
        SQL_SERVER=sqlservername.database.windows.net
        ```
3. Create a python environment
4. Import the requirements.txt `pip install -r requirements.txt`
5. From the window, run `streamlit run viz_v2.py`
6. If you are a Mac user, please follow [this](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos?view=sql-server-ver16) to install ODBC for PYODBC