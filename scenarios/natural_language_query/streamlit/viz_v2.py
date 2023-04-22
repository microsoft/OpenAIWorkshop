import streamlit as st
import os
import pandas as pd
import sys
import numpy as np
import plotly.express as px
import plotly.graph_objs as go

sys.path.append('../')
from analyze_v2 import AnalyzeGPT, SQL_Query, ChatGPT_Handler
import openai
import streamlit as st  

from dotenv import load_dotenv

from pathlib import Path  # Python 3.6+ only

system_message="""
You are a smart AI assistant to help answer business questions based on analyzing data. 
You can plan solving the question with one more multiple thought step. At each thought step, you can write python code to analyze data to assist you. Observe what you get at each step to plan for the next step.
You are given following utilities to help you retrieve data and commmunicate your result to end user.
1. execute_sql(sql_query: str): A Python function can query data from the database given the query that you need to create which need to be syntactically correct for {sql_engine}. It return a Python pandas dataframe contain the results of the query.
2. Use plotly library for data visualization. 
3. Use observe(label: str, data: any) utility function to observe data under the label for your evaluation. Use observe() function instead of print() as this is executed in streamlit environment. Due to system limitation, you will only see the first 10 rows of the dataset.
4. To communicate with user, use show() function on data, text and plotly figure. show() is a utility function that can render different types of data to end user. Remember, you don't see data with show(), only user does. You see data with observe()
    - If you want to show  user a plotly visualization, then use ```show(fig)`` 
    - If you want to show user data which is a text or a pandas dataframe or a list, use ```show(data)```
    - Never use print(). User don't see anything with print()
5. Lastly, don't forget to deal with data quality problem. You should apply data imputation technique to deal with missing data or NAN data.
6. Always follow the flow of Thought: , Observation:, Action: and Answer: as in template below strictly. 

"""

few_shot_examples="""
<<Template>>
Question: User Question
Thought 1: Your thought here.
Action: 
```Python
#Import neccessary libraries here
import numpy as np
#Query some data 
sql_query = "SOME SQL QUERY"
step1_df = execute_sql(sql_query)
# Replace 0 with NaN. Always have this step
step1_df['Some_Column'] = step1_df['Some_Column'].replace(0, np.nan)
#observe query result
observe("some_label", step1_df) #Always use observe() instead of print
```
Observation: 
step1_df is displayed here
Thought 2: Your thought here
Action:  
```Python
import plotly.express as px 
#from step1_df, perform some data analysis action to produce step2_df
#To see the data for yourself the only way is to use observe()
observe("some_label", step2_df) #Always use observe() 
#Decide to show it to user.
fig=px.line(step2_df)
#visualize fig object to user.  
show(fig)
#you can also directly display tabular or text data to end user.
show(step2_df)
```
Observation: 
step2_df is displayed here
Answer: Your final answer and comment for the question
<</Template>>

"""
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)


openai.api_type = "azure"
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
temperature=0

sqllite_db_path= os.environ.get("SQLITE_DB_PATH","data/northwind.db")

extract_patterns=[("Thought:",r'(Thought \d+):\s*(.*?)(?:\n|$)'), ('Action:',r"```Python\n(.*?)```"),("Answer:",r'([Aa]nswer:) (.*)')]

extractor = ChatGPT_Handler(extract_patterns=extract_patterns)
faq_dict = {  
    "ChatGPT": [  
        "Show me daily revenue trends in 2016 per region",  
        "Is that true that top 20% customers generate 80% revenue in 2016? What's their percentage of revenue contribution?",  
        "Which products have most seasonality in sales quantity in 2016?",  
        "Which customers are most likely to churn?", 
        "What is the impact of discount on sales? What's optimal discount rate?" 
    ],  
    "GPT-4": [  
        "Predict monthly revenue for next 12 months starting from June-2018",  
        "What is the impact of discount on sales? What's optimal discount rate?" ,  
    ]  
}  

st.sidebar.title('Data Analysis Assistant')

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

chatgpt_deployment = load_setting("AZURE_OPENAI_CHATGPT_DEPLOYMENT","gpt-35-turbo")  
gpt4_deployment = load_setting("AZURE_OPENAI_GPT4_DEPLOYMENT","gpt-35-turbo")  
endpoint = load_setting("AZURE_OPENAI_ENDPOINT","https://resourcenamehere.openai.azure.com/")  
api_key = load_setting("AZURE_OPENAI_API_KEY")  
sql_engine = load_setting("SQL_ENGINE","sqlite")
dbserver = load_setting("SQL_SERVER")
database = load_setting("SQL_DATABASE")
db_user = load_setting("SQL_USER")
db_password = load_setting("SQL_PASSWORD")

with st.sidebar:  
    # Create settings button  
    # if 'show_settings' not in st.session_state:  
    #     st.session_state['show_settings'] = False  
    # if st.button("Settings"):  
    #     st.session_state['show_settings'] = not st.session_state['show_settings']  
    # if st.session_state['show_settings']:  
    with st.expander("Settings"):
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


        sql_engine = st.selectbox('SQL Engine',["sqlite", "sqlserver"])  
        if sql_engine =="sqlserver":
            dbserver = st.text_input("SQL Server:", value=dbserver)  
            database = st.text_input("SQL Server Database:", value=database)  
            db_user = st.text_input("SQL Server db_user:", value=db_user)  
            db_password = st.text_input("SQL Server Password:", value=db_password, type="password")

        save_setting("SQL_ENGINE", sql_engine)  
        save_setting("SQL_SERVER", dbserver)  
        save_setting("SQL_DATABASE", database) 
        save_setting("SQL_USER", db_user)   
        save_setting("SQL_PASSWORD", db_password)  

    gpt_engine = st.selectbox('GPT Model', ["ChatGPT", "GPT-4"])  
    if gpt_engine == "ChatGPT":  
        gpt_engine = chatgpt_deployment  
        faq = faq_dict["ChatGPT"]  
    else:  
        gpt_engine = gpt4_deployment  
        faq = faq_dict["GPT-4"]  
    option = st.selectbox('FAQs',faq)  

    if gpt_engine!="":
    
        sql_engine = load_setting("SQL_ENGINE")
        dbserver = load_setting("SQL_SERVER")  
        database = load_setting("SQL_DATABASE")
        db_user = load_setting("SQL_USER")
        db_password = load_setting("SQL_PASSWORD")
        if sql_engine =="sqlserver":
            #TODO: Handle if there is not a driver here
            sql_query_tool = SQL_Query(driver='ODBC Driver 17 for SQL Server',dbserver=dbserver, database=database, db_user=db_user ,db_password=db_password)
        else:
            sql_query_tool = SQL_Query(db_path=sqllite_db_path)

        analyzer = AnalyzeGPT(sql_engine=sql_engine,content_extractor= extractor, sql_query_tool=sql_query_tool,  system_message=system_message, few_shot_examples=few_shot_examples,st=st,  
                            gpt_deployment=gpt_engine,max_response_tokens=max_response_tokens,token_limit=token_limit,  
                            temperature=temperature)  

    show_code = st.checkbox("Show code", value=False)  
    question = st.text_area("Ask me a question", option)
    openai.api_key = api_key
    openai.api_base = endpoint
  
    if st.button("Submit"):  
        if chatgpt_deployment=="" or endpoint=="" or api_key=="":
            col1.error("You need to specify Open AI Deployment Settings!", icon="🚨")
        else:
            for key in st.session_state.keys():
                if "AZURE_OPENAI" not in key and "settings" and "SQL" not in key : 
                    del st.session_state[key]  

            analyzer.run(question,show_code, col1)  
