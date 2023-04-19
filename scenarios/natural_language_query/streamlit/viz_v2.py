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

faq =["Show me daily revenue trends in 2016  per region","Is that true that top 20% customers generate 80% revenue in 2016?","Which products have most seasonality in sales quantity in 2016?", "Which customers are most likely to churn?", "Predict monthly revenue for next 12 months starting from June-2018"]
# additional_database_comments="the dimension.Date table can be joined with other table via the column DATE"

system_message="""
You are a smart AI assistant to help answer business questions based on analyzing data. 
You can plan solving the question with one more multiple thought step. At each thought step, you can write python code to analyze data to assist you. Observe what you get at each step to plan for the next step.
You are given following utilities to help you retrieve data and commmunicate your result to end user.
1. execute_sql(sql_query: str): A Python function can query data from the database given the query that you need to create which need to be syntactically correct for {sql_engine}. It return a Python pandas dataframe contain the results of the query.
2. Use plotly library for data visualization. 
3. Use observe(label: str, data: any) utility function to observe data under the label for your evaluation. Use observe() function instead of print() as this is executed in streamlit environment.
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
gpt4_deployment=os.environ.get("AZURE_OPENAI_GPT4_DEPLOYMENT","gpt-4")
chatgpt_deployment=os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT","gpt-35-turbo")

database=os.environ.get("SQL_DATABASE","WorldWideImportersDW")
dbserver=os.environ.get("SQL_SERVER","someazureresource.database.windows.net")
db_user=os.environ.get("SQL_USER","MissingSQLUser")
db_password= os.environ.get("SQL_PASSWORD","MissingSQLPassword")
sql_engine= os.environ.get("SQL_ENGINE","sqlite")
sqllite_db_path= os.environ.get("SQLITE_DB_PATH","../data/northwind.db")

extract_patterns=[("Thought:",r'(Thought \d+):\s*(.*?)(?:\n|$)'), ('Action:',r"```Python\n(.*?)```"),("Answer:",r'([Aa]nswer:) (.*)')]

extractor = ChatGPT_Handler(extract_patterns=extract_patterns)
# sql_query_tool = SQL_Query(driver='ODBC Driver 17 for SQL Server',dbserver=dbserver, database=database, db_user=db_user ,db_password=db_password)
sql_query_tool = SQL_Query(db_path=sqllite_db_path)
gpt_engine = ["ChatGPT", "GPT-4"]
st.sidebar.title('Data Analysis Assistant')

col1, col2  = st.columns((3,1)) 
with st.sidebar:
    gpt_engine = st.selectbox('GPT Model',gpt_engine)
    if gpt_engine=="ChatGPT":
        gpt_engine= chatgpt_deployment
    else:
        gpt_engine= gpt4_deployment

    option = st.selectbox('FAQs',faq)

    analyzer = AnalyzeGPT(sql_engine=sql_engine,content_extractor= extractor, sql_query_tool=sql_query_tool,  system_message=system_message, few_shot_examples=few_shot_examples,st=st, 
                        gpt_deployment=gpt_engine,max_response_tokens=max_response_tokens,token_limit=token_limit,
                        temperature=temperature)

    show_code = st.checkbox("Show code", value=False)  
    # step_break = st.checkbox("Break at every step", value=False)  
    question = st.text_area("Ask me a  question on churn", option)
    if st.button("Submit"):  
        # analyzer.run(question,show_code,step_break, col1)
        for key in st.session_state.keys():
            del st.session_state[key]

        analyzer.run(question,show_code, col1)

    # if st.button("Start Over"):
    #     # Call the execute_query function with the user's question 
    #     # Delete all the items in Session state
    #     for key in st.session_state.keys():
    #         del st.session_state[key]
    #     col1.empty()

