import streamlit as st
import random
import pandas as pd
import sys
sys.path.append('../')
from analyze import AnalyzeGPT
import openai
import os
from dotenv import load_dotenv

tables_structure="""
Table	Column	Description
GA_SESSION  SESSION_ID	Unique ID of a user session
GA_SESSION  VISIT_NUMBER	Number of times the user has visited the docusign website 
GA_SESSION  DEVICE_DEVICE_CATEGORY	mobile or desktop
GA_SESSION  DEVICE_OPERATING_SYSTEM	OS of the user's device
GA_SESSION  DEVICE_BROWSER	browser used by the user
GA_SESSION  CHANNEL_GROUPING	last touched channel that the user came to the site from
GA_SESSION  TOTAL_PAGEVIEWS	Total pageviews during each session
GA_SESSION  GEO_NETWORK_CONTINENT	user's continent
GA_SESSION  F_ALLTRIAL_START	user landed on the trial page 
GA_SESSION  F_ALLTRIAL_COMPLETE	user completed trial sign up 
GA_SESSION  F_PURCHASE_INTENT	view plan and pricing page
GA_SESSION  F_PURCHASE_START	start cart 
GA_SESSION  F_PURCHASE_COMPLETE	complete purchase 
GA_EVENTS   SESSION_ID	Unique ID of a user session
GA_EVENTS   HIT_NUMBER	Sequence of events performed by the user during the session
GA_EVENTS   IS_ENTRANCE	the first page user landed in during the session
GA_EVENTS   IS_EXIT	the last page user visited during the session
GA_EVENTS   PAGE_PATH_CLEAN	page url
GA_EVENTS   SITE_SECTION	Classifying the webpages into various sections based on the page visited by user
GA_EVENTS   SITE_CATEGORY	Grouping sections into categories
GA_EVENTS   TYPE	has values page and event. Shows if the user navigated to a page or performed an event on the page 

GA_SESSION contains sessions of users who have completed a purchase. SESSION_ID is the primary key and all events are stored in GA_EVENTS table.
The GA_EVENTS contains all actions performed by the user. SESSION_ID+HIT_NUMBER is the primary key. The HIT_NUMBER in the GA_EVENTS table will give the sequence of events a customer performed when completing the purchase 
You can outer join two data sets using user id (GA_SESSION.SESSION_ID = GA_EVENTS.SESSION_ID). 

The path to purchase can be traced using fields in the GA_EVENTS table.
PAGE_PATH_CLEAN : URL of the page
SITE_SECTION: Classifying the webpages into various sections based on the page visited by user
SITE_CATEGORY: Grouping sections into categories
A completed purchase is identified by F_PURCHASE_COMPLETE = 1 in GA_SESSION table.
"""

system_message="""
You are a smart AI assistant to help answer session and event questions by querying data from Microsoft SQL Server Database. 
Only use the table and columns in provided in the <<Database structure>> to write queries. Use Microsoft SQL Server compliant query syntax.
Given the Question, generate the SQL query that provides information to answer the question.
"""
few_shot_examples="""
<<Examples to follow:>>
Question: Help me calculate the conversion rate.
Thought 1: First I need to calculate the count of unique events at step1_cta_events,users at step2_pnp_events, and unique users who have gone through BOTH step1_cta_events AND made the final purchase at step2_pnp_events (NAME = 'Account Purchase')
Action 1: Query[SELECT COUNT(DISTINCT s1.DISTINCT_ID) AS Step1_Users, COUNT(DISTINCT s2.DISTINCT_ID) AS Step2_Users, COUNT(DISTINCT CASE WHEN s2.NAME = 'Account Purchase' THEN s1.DISTINCT_ID END) AS Converted_Users\nFROM step1_cta_events s1\nLEFT JOIN step2_pnp_events s2 ON s1.DISTINCT_ID = s2.DISTINCT_ID;]
Observation 1: 
Step1_Users	Step2_Users	Converted_Users
735978	117106	31167
Thought 2: I can now calculate the  conversion rate.
Action 2: Query[SELECT CAST(31167 AS FLOAT) / CAST(735978 AS FLOAT) AS Conversion_Rate;]
Observation 2: 0.042347733220286475
Thought 3: Now I have the conversion rate
Action 3: Answer[The overall conversion rate is 0.0423477332]
Question: Show me top 20 best selling products in 2013
Thought 1: I need to query revenue for each month in 2013 for top 3 customers from Fact.Sales table and join with Dimension.Customer to get customer information and join with Dimension.Date to get time information. Then I need to group data by month and customer and sort data by revenue. Finally, I need to visualize data using line chart to show monthly revenue trends for each customer.
Action 1: Query[SELECT c.Customer, d.Calendar_Month_Label, SUM(s.Total_Including_Tax) AS Revenue FROM Fact.Sale s JOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key JOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date WHERE d.Calendar_Year = 2013 GROUP BY c.Customer, d.Calendar_Month_Label HAVING c.Customer IN (SELECT TOP 3 c.Customer FROM Fact.Sale s JOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key JOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date WHERE d.Calendar_Year = 2013 GROUP BY c.Customer ORDER BY SUM(s.Total_Including_Tax) DESC) ORDER BY c.Customer ASC, d.Calendar_Month_Number ASC;], Python[```\nimport plotly.express as px\n\ndef visualize_data(sql_result_df):\n    fig=px.line(sql_result_df, x='Calendar_Month_Label', y='Revenue', color='Customer', title='Monthly Revenue Trends in 2013 for Top 3 Customers')\n    return fig\n```]
Observation 1: ('42000', '[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Column "Dimension.Date.Calendar_Month_Number" is invalid in the ORDER BY clause because it is not contained in either an aggregate function or the GROUP BY clause. (4108) (SQLExecDirectW)')
Thought 2: SQL query returned error, I need to correct the syntax for my query based on the error message
Action 2: Query[SELECT c.Customer, d.Calendar_Month_Label, SUM(s.Total_Including_Tax) AS Revenue FROM Fact.Sale s JOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key JOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date WHERE d.Calendar_Year = 2013 GROUP BY c.Customer, d.Calendar_Month_Label,d.Calendar_Month_Number HAVING c.Customer IN (SELECT TOP 3 c.Customer FROM Fact.Sale s JOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key JOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date WHERE d.Calendar_Year = 2013 GROUP BY c.Customer ORDER BY SUM(s.Total_Including_Tax) DESC) ORDER BY c.Customer ASC, d.Calendar_Month_Number ASC;], Python[```\nimport plotly.express as px\n\ndef visualize_data(sql_result_df):\n    fig=px.line(sql_result_df, x='Calendar_Month_Label', y='Revenue', color='Customer', title='Monthly Revenue Trends in 2013 for Top 3 Customers')\n    return fig\n```]
Observation 2: Region                                      Stock_Item Total_Sales
0    Americas  "The Gu" red shirt XML tag t-shirt (Black) 3XL  1433516.40
1    Americas  "The Gu" red shirt XML tag t-shirt (Black) 3XS  1395759.60
Thought 3: The result answers the question
Action 3: Answer[The result is provided]
"""
load_dotenv()
openai.api_type = "azure"
openai.api_key = os.environ.get("AOAI_KEY","Enter your key here")
openai.api_base = os.environ.get("AOAI_ENDPOINT","https://azopenaidemo.openai.azure.com/")  # SET YOUR RESOURCE ENDPOINT
openai.api_version = os.environ.get("AOAI_VERSION","2023-03-15-preview")  
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="gpt-35-turbo"
database=os.environ.get("DB_NAME","Database")
dbserver=os.environ.get("SQL_SERVER_NAME","Servername with database.windows.net")
db_user=os.environ.get("DB_USER","Enter user name")
db_password=os.environ.get("DB_PWD","Enter user name")
driver=os.environ.get("SQL_DRIVER","ODBC Driver 18 for SQL Server")
print(f'driver={driver}')

analyzer = AnalyzeGPT(tables_structure, system_message,few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a question sessions and events")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)



