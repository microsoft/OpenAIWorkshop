import streamlit as st
import os
import pandas as pd
import sys
import numpy as np
import plotly.express as px
import plotly.graph_objs as go

sys.path.append('../')
from analyze_v1 import AnalyzeGPT, SQL_Query, ChatGPT_Handler
import openai
import streamlit as st  

from dotenv import load_dotenv

from pathlib import Path  # Python 3.6+ only


system_message="""
You are an agent designed to interact with a SQL database with schema detail in <<data_sources>>.
Given an input question, create a syntactically correct {sql_engine} query to run, then look at the results of the query and return the answer.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for a the few relevant columns given the question.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
Remember to format SQL query as in ```sql\n SQL QUERY HERE ``` in your response.

"""
few_shot_examples=""


env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

openai.api_type = "azure"
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
temperature=0

sqllite_db_path= os.environ.get("SQLITE_DB_PATH","data/northwind.db")

extract_patterns=[('sql',r"```sql\n(.*?)```")]

extractor = ChatGPT_Handler(extract_patterns=extract_patterns)
sql_query_tool = SQL_Query(db_path=sqllite_db_path)
gpt_engine = ["ChatGPT", "GPT-4"]
faq_dict = {  
    "ChatGPT": [  
        "Show me revenue by product in ascending order",  
        "Show me net revenue by year. Revenue time is based on shipped date.",  
        "For each category, get the list of products sold and the total sales amount", 
    ],  
    "GPT-4": [  
        "Pick top 20 customers generated most revenue in 2016 and for each customer show 3 products that they purchased most",  
        "Which products have most seasonality in sales quantity in 2016?" ,  
    ]  
}  

st.sidebar.title('SQL Query Writing Assistant')

col1, col2  = st.columns((3,1)) 
def save_setting(setting_name, setting_value):  
    """  
    Function to save the setting information to session  
    """  
    st.session_state[setting_name] = setting_value  
  
def load_setting(setting_name, default_value=''):  
    """  
    Function to load the setting information from session  
    """  
    if  os.environ.get(setting_name) is not None:
        return os.environ.get(setting_name)
    if setting_name not in st.session_state:  
        st.session_state[setting_name] = default_value  
    return st.session_state[setting_name]  

chatgpt_deployment = load_setting("AZURE_OPENAI_CHATGPT_DEPLOYMENT")  
gpt4_deployment = load_setting("AZURE_OPENAI_GPT4_DEPLOYMENT")  
endpoint = load_setting("AZURE_OPENAI_ENDPOINT")  
api_key = load_setting("AZURE_OPENAI_API_KEY")  
sql_engine = load_setting("SQL_ENGINE")
dbserver = load_setting("SQL_SERVER")
database = load_setting("SQL_DATABASE")
db_user = load_setting("SQL_USER")
db_password = load_setting("SQL_PASSWORD")
if sql_engine =="sqlserver":
    sql_query_tool = SQL_Query(driver='ODBC Driver 17 for SQL Server',dbserver=dbserver, database=database, db_user=db_user ,db_password=db_password)
else:
    sql_query_tool = SQL_Query(db_path=sqllite_db_path)

with st.sidebar:  
    # Create settings button  
    if 'show_settings' not in st.session_state:  
        st.session_state['show_settings'] = False  
    if st.button("Settings"):  
        st.session_state['show_settings'] = not st.session_state['show_settings']  
    if st.session_state['show_settings']:  
        
        chatgpt_deployment = st.text_input("ChatGPT deployment name:", value=chatgpt_deployment)  
        gpt4_deployment = st.text_input("GPT-4 deployment name (if not specified, default to ChatGPT's):", value=gpt4_deployment) 
        if gpt4_deployment=="":
            gpt4_deployment= chatgpt_deployment 
        endpoint = st.text_input("Azure OpenAI Endpoint:", value=endpoint)  
        api_key = st.text_input("Azure OpenAI Key:", value=api_key, type="password")

        save_setting("AZURE_OPENAI_CHATGPT_DEPLOYMENT", chatgpt_deployment)  
        save_setting("AZURE_OPENAI_GPT4_DEPLOYMENT", gpt4_deployment)  
        save_setting("AZURE_OPENAI_ENDPOINT", endpoint)  
        save_setting("AZURE_OPENAI_API_KEY", api_key)  

        if sql_engine == "sqlserver":
            sql_engine_list = [ "sqlserver", "sqlite"]
            print(sql_engine_list)
        else:
            sql_engine_list = ["sqlite", "sqlserver"]
        sql_engine = st.selectbox('SQL Engine',sql_engine_list)  
        if sql_engine =="sqlserver":
            dbserver = st.text_input("SQL Server:", value=dbserver)  
            database = st.text_input("SQL Server Database:", value=database)  
            db_user = st.text_input("SQL Server db_user:", value=db_user)  
            db_password = st.text_input("SQL Server Password:", value=db_password, type="password")
            sql_query_tool = SQL_Query(driver='ODBC Driver 17 for SQL Server',dbserver=dbserver, database=database, db_user=db_user ,db_password=db_password)
            save_setting("SQL_ENGINE", sql_engine)  
            save_setting("SQL_SERVER", dbserver)  
            save_setting("SQL_DATABASE", database) 
            save_setting("SQL_USER", db_user)   
            save_setting("SQL_PASSWORD", db_password)  

        else:
            sql_query_tool = SQL_Query(db_path=sqllite_db_path)



    gpt_engine = st.selectbox('GPT Model', ["ChatGPT", "GPT-4"])  
    if gpt_engine == "ChatGPT":  
        gpt_engine = chatgpt_deployment  
        faq = faq_dict["ChatGPT"]  
    else:  
        gpt_engine = gpt4_deployment  
        faq = faq_dict["GPT-4"]  
    option = st.selectbox('FAQs',faq)  

    if gpt_engine!="":
        analyzer = AnalyzeGPT(sql_engine=sql_engine,content_extractor= extractor, sql_query_tool=sql_query_tool,  system_message=system_message, few_shot_examples=few_shot_examples,st=st,  
                            gpt_deployment=gpt_engine,max_response_tokens=max_response_tokens,token_limit=token_limit,  
                            temperature=temperature)  

    show_code = st.checkbox("Show code", value=False)  
    # step_break = st.checkbox("Break at every step", value=False)  
    question = st.text_area("Ask me a question", option)
    openai.api_key = api_key
    openai.api_base = endpoint
  
    if st.button("Submit"):  
        if chatgpt_deployment=="" or endpoint=="" or api_key=="":
            st.write("You need to specify Open AI Deployment Settings!")
        else:
            for key in st.session_state.keys():
                if ("AZURE_OPENAI" not in key )and ("settings" not in key) and ("SQL" not in key) : 
                    del st.session_state[key]  

            analyzer.run(question,show_code, col1)  
