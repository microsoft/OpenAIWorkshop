# Overview
This application demonstrate the of Open AI (ChatGPT/GPT-4) to help answer business questions by performing advanced data analytic tasks on a business database.
Examples of questions are:
- Simple:Show me daily revenue trends in 2016  per region
- More difficult: Is that true that top 20% customers generate 80% revenue in 2016?
- Advanced: Predict monthly revenue for next 12 months starting from June-2018
The application support Python's built-in SQLITE as well as Microsoft SQL Server.
# Instructions
1. Create an Azure OpenAI deployment in an Azure subscription with a GPT-35-Turbo deployment
1. Create a `secrets.env` file in the root of this folder
    ```txt
    AZURE_OPENAI_API_KEY=9999999999999999999999999
    AZURE_OPENAI_ENDPOINT=https://openairesourcename.openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
    SQL_USER=sqluserid
    SQL_PASSWORD=sqlpassword
    SQL_DATABASE=WideWorldImportersDW
    SQL_SERVER=sqlservername.database.windows.net
    ```
1. Create a python environment
1. Import the requirements.txt `pip install -r requirements.txt`
1. From the window, run `streamlit run viz.py`

# Database configuration
If you want to setup the database there is a [bacpac for the installer](../../../data/WideWorldImportersDW-Custom.bacpac) in the folder. 
