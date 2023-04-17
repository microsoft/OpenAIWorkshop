import streamlit as st
import os
import pandas as pd
import sys
sys.path.append('../')
from analyze_v2 import AnalyzeGPT, SQL_Query, ChatGPT_Handler
import openai
import streamlit as st  

from dotenv import load_dotenv

from pathlib import Path  # Python 3.6+ only

faq =["Is that true that top 20% customers generate 80% revenue in 2016?","Which products have most seasonality in sales quantity in 2016?", "Which customers are most likely to churn?", " Predicts next 3 months revenue"]
additional_database_comments="the dimension.Date table can be joined with other table via the column DATE"

system_message="""
You are a smart AI assistant to help answer business questions based on analyzing data. 
You can plan solving the question with one more multiple thought step. At each thought step, you can write python code to analyze data to assist you. Observe what you get at each step to plan for the next step.
You are given following utilities to help you retrieve data and commmunicate your result to end user.
1. execute_sql(sql_query: str): A Python function can query data from the database given the query that you need to create which need to be syntactically correct for {sql_engine}. It return a Python pandas dataframe contain the results of the query.
2. Use plotly library for data visualization. 
3. streamlit's self.st object for you to persist and reload data between thought steps and visualize data to end user. 
    - If you want to reuse the result of a computation in a step (e.g. step1_df), alway persist it with this code ```self.st.session_state['step1_df'] = step1_df``` then 
    in another step, use this code to restore the step1_df ```step1_df = self.st.session_state['step1_df']```
    - If you want to show  user a plotly visualization, then use ```st.plotly_chart(fig)`` 
    - If you want to show user non-chart data, use ```st.write(data)```
4. Use observe(label: str, data: any) utility function to observe data under the label for your visual evaluation. Use observe() function instead of print() as this is executed in streamlit environment.
Always follow the flow of Thought: , Observation:, Action: and Answer: as in template below strictly. 
"""

few_shot_examples="""
<<Template>>
Question: User Question
Thought 1: Your thought here.
Action: 
```Python
#Import neccessary libraries here
#Query some data 
sql_query = "SOME SQL QUERY"
step1_df = execute_sql(sql_query)
#persist data
self.st.session_state['step1_df'] = step1_df
#observe query result
observe("some_label", step1_df) #Always use observe() instead of print
```
Observation: data from step1_df

Thought 2: Your thought here
Action:  
```Python
import plotly.express as px 
#perform some data analysis action
#load data from step 1
step1_df = self.st.session_state['step1_df']
#do some more work and have step2_df result. Decide to show it to user.
fig=px.line(step2_df)
#visualize fig object in streamlit for user. Remember to use st directly instead of self.st 
st.plotly_chart(fig)
#you can also directly display tabular or text data using. DO NOT use print().
st.write(step2_df)
#also observe it yourself to make comment.
observe("some_label", step2_df) #Always use observe() 
```
Observation: data from step2_df
Answer: Your final answer and comment for the question
<</Template>>

"""
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

# Check if secrets.env exists and if not error out
if not os.path.exists("secrets.env"):
    print("Missing secrets.env file with environment variables. Please create one and try again. See README.md for more details")
    exit(1)

# NOTE: You need to create a secret.env file to run this in the same folder with these variables
openai.api_type = "azure"
openai.api_key = os.environ.get("AZURE_OPENAI_API_KEY","OpenAPIKeyMissing")
openai.api_base = os.environ.get("AZURE_OPENAI_ENDPOINT","OpenAPIEndpointMissing")
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
temperature=0
gpt_deployment_master=os.environ.get("AZURE_OPENAI_DEPLOYMENT_MASTER_NAME","gpt-4")
gpt_deployment_tool=os.environ.get("AZURE_OPENAI_DEPLOYMENT_TOOL_NAME","gpt-35-turbo")

database=os.environ.get("SQL_DATABASE","WorldWideImportersDW")
dbserver=os.environ.get("SQL_SERVER","someazureresource.database.windows.net")
db_user=os.environ.get("SQL_USER","MissingSQLUser")
db_password= os.environ.get("SQL_PASSWORD","MissingSQLPassword")
sql_engine= os.environ.get("SQL_ENGINE","sqlite")
sqllite_db_path= os.environ.get("SQLITE_DB_PATH","../data/northwind.db")

extract_patterns=[("Thought:",r'(Thought \d+):\s*(.*?)(?:\n|$)'), ('Action:',r"```Python\n(.*?)```"),("Answer:",r'([Aa]nswer:?) (.*)')]

extractor = ChatGPT_Handler(gpt_deployment=gpt_deployment_tool,max_response_tokens=max_response_tokens,token_limit=token_limit,temperature=temperature,extract_patterns=extract_patterns)
# sql_query_tool = SQL_Query(driver='ODBC Driver 17 for SQL Server',dbserver=dbserver, database=database, db_user=db_user ,db_password=db_password)
sql_query_tool = SQL_Query(db_path=sqllite_db_path)

analyzer = AnalyzeGPT(sql_engine=sql_engine,content_extractor= extractor, sql_query_tool=sql_query_tool,  system_message=system_message, few_shot_examples=few_shot_examples,st=st, 
                      gpt_deployment=gpt_deployment_tool,max_response_tokens=max_response_tokens,token_limit=token_limit,
                      temperature=temperature)
st.sidebar.title('Data Analysis Assistant')

col1, col2  = st.columns((3,1)) 
with st.sidebar:
    option = st.selectbox('FAQs',faq)
    question = st.text_area("Ask me a  question on churn", option)
    if st.button("Submit"):  
        # Call the execute_query function with the user's question 
        # Delete all the items in Session state
        for key in st.session_state.keys():
            del st.session_state[key]

        analyzer.run(question, col1)