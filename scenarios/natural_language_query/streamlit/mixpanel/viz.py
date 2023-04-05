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

Table dbo.step2_pnp_events sample data

NAME	TIME_DATE	ACCOUNT_ID	DISTINCT_ID
Account Purchase	2022-08-11 00:00:00.0000000	fffe8cff8ba0fc2c007ffbdfbaf1e761f1adc7f1	ffff0721ce21ff4e81569e6904528e371bba23bd
Buy Now Button Click	2022-08-11 00:00:00.0000000	fffdf364a7d600c8241143f2dd78fce34e94057e	ffffae2645006847adeae9fbf9faf7ac80f67ee2
Checkout 2 (Payment)	2022-08-10 00:00:00.0000000	fffe8cff8ba0fc2c007ffbdfbaf1e761f1adc7f1	ffffae2645006847adeae9fbf9faf7ac80f67ee2
Checkout 3 (Payment)	2022-06-15 00:00:00.0000000	b89566b1ee85539fc26ef032e03caa14916f3f14	8c857c24343c17d620651f1f9128f8a9875de938
Purchase Click	2022-08-11 00:00:00.0000000	fffe8cff8ba0fc2c007ffbdfbaf1e761f1adc7f1	ffffae2645006847adeae9fbf9faf7ac80f67ee2
View Signup Pricing	2022-08-13 00:00:00.0000000	fffdf364a7d600c8241143f2dd78fce34e94057e	ffffae2645006847adeae9fbf9faf7ac80f67ee2
View Upgrade Pricing	2022-08-11 00:00:00.0000000	ffff59d01b3047a8db9e0f45f59824511162fe11	ffffba6e77cd1125d7a5a3b87267975fdae99511

Table step1_cta_events sample data

CTA_EVENT	EVENT_DATE	MIXPANEL_ACCOUNT_ID	DISTINCT_ID
Blue View Plan CTA	2023-01-31 00:00:00.0000000	ffffd59c877df0aba221733d6d870ca60419d2f8	ffffecb49449b41f95bdc3aa04461934f8b5ff45
Red Banner	2023-01-31 00:00:00.0000000	ffffb1b5a13e88e6e16fb6853912f09c52e0915a	ffff0cb96dc4cb3d9ff79726688d623f82757732
Upgrade Modal	2023-01-31 00:00:00.0000000	ffffb1b5a13e88e6e16fb6853912f09c52e0915a	ffff42a82e255c87bd3b0ad5897157c8ee3db0e6

step1_cta_events contains event logs of top-of-the-funnel actions by user id and account id. After engaging with these events, users will land on the same Pricing and Plan page and go through the checkout process, which are recorded in step2_pnp_events file. 
The order of step2_pnp_events  starts with View Upgrade Pricing or View Signup Pricing, then Buy Now Button Click, then Checkout: Step - Payment or Checkout 2 (Payment) or Checkout 3 (Payment), then Purchase Click, then Account Purchase.
You can outer join two data sets using user id (step1_cta_events.DISTINCT_ID = dbo.step2_pnp_events.DISTINCT_ID). 

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
Thought 1: First I need to calculate the count of unique events at step1_cta_events 
Action 1: Query[SELECT CAST(COUNT(DISTINCT DISTINCT_ID) as FLOAT) AS Clicks  FROM step1_cta_events]
Observation 1: 735978
Thought 2: I now need to the counts of unique events at step1_cta_events that convert into Account Purchase at step2_pnp_events. As there are two ways to join the two tables, I need to join using user id then join using account id then union the result before count
Action 2: Query[SELECT CAST(COUNT(DISTINCT DISTINCT_ID) AS FLOAT) FROM(SELECT CTA_EVENT,s1.DISTINCT_ID, NAME\nFROM step1_cta_events s1\nJOIN step2_pnp_events s2 ON s1.DISTINCT_ID = s2.DISTINCT_ID\nWHERE NAME = 'Account Purchase'\nUNION ALL\nSELECT CTA_EVENT, s1.DISTINCT_ID, NAME\nFROM step1_cta_events s1\nJOIN step2_pnp_events s2 ON s1.MIXPANEL_ACCOUNT_ID = s2.ACCOUNT_ID\nWHERE NAME = 'Account Purchase') as union_result]\n
Observation 2: 31380
Thought 3: Now I need to divide the result at step 2 by the result at step 1 to get the result
Action 3: Query[SELECT 31380.0 / 735978.0 AS Result ]
Observation 4: 0.042637144
Thought 4: Result came back as 0.042637144
Action 4: Answer[The conversion rate is 0.042637144]
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
openai.api_key = ""  # SET YOUR OWN API KEY HERE
openai.api_base = "https://.openai.azure.com/" # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="gpt-35-turbo"
database=""
dbserver=".database.windows.net"
db_user=""
db_password= ""
analyzer = AnalyzeGPT(tables_structure, system_message,few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a  question in sales")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)


