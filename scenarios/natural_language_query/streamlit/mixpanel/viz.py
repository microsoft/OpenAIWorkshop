import streamlit as st
import random
import pandas as pd
import sys
sys.path.append('../')
from analyze import AnalyzeGPT
import openai

tables_structure="""
Table	Column	Description
step1_cta_events	EVENT_DATE	when an event happened
step1_cta_events	CTA_EVENT	click-through actions
step1_cta_events	MIXPANEL_ACCOUNT_ID	account id
step1_cta_events	DISTINCT_ID	user id
step2_pnp_events	TIME::DATE	when an event happened
step2_pnp_events	NAME	event name
step2_pnp_events	EVENT_ID	event id
step2_pnp_events	DISTINCT_ID	user id
step2_pnp_events	ACCOUNT_ID	account id

step1_cta_events contains event logs of top-of-the-funnel actions by user id and account id. After engaging with these events, users will land on the same Pricing and Plan page and go through the checkout process, which are recorded in step2_pnp_events file. 
The order of step2_pnp_events  starts with View Upgrade Pricing or View Signup Pricing, then Buy Now Button Click, then Checkout: Step - Payment or Checkout 2 (Payment) or Checkout 3 (Payment), then Purchase Click, then Account Purchase.
You can outer join two data sets using user id (step1_cta_events.DISTINCT_ID = step2_pnp_events.DISTINCT_ID). 

"""

system_message="""
You are a smart AI assistant to help answer marketing analysis questions by querying data from Microsoft SQL Server Database and visualizing data with plotly. 
In the examples below, questions are broken down into one or several  parts to be analyzed and eventually to answer the main question.
The action after each thought can be a data query and data visualization code or it can be final answer. 
To help you understand the domain, here are some additional background useful knowledge:
- Conversion  is defined as the ratio of the count of unique userids who have gone through BOTH step1_cta_events AND made the final purchase at step2_pnp_events (NAME = 'Account Purchase' ) to the count of unique users at CTA step1_cta_events who may or may not have gone to step2_pnp_events 
- Conversion might need to be broken down by step, which mean by a starting event in step1_cta_events.
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
openai.api_type = "azure"
openai.api_key = "6b134b679f0e4a5b90925cdca6eaf391"  # SET YOUR OWN API KEY HERE
openai.api_base = "https://azopenaidemo.openai.azure.com/" # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="gpt-35-turbo"
database="DocuSignOpenAI"
dbserver="oaisqldemo.database.windows.net"
db_user="oaireaderuser"
db_password= "Oaiworkshop@password123"
analyzer = AnalyzeGPT(tables_structure, system_message,few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a  question in sales")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)



