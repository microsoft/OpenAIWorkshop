import streamlit as st
import random
import pandas as pd
import sys
from analyze import AnalyzeGPT
import openai

tables_structure="""
    - Given the table account_usage has following columns:
ACCOUNTID_M		Masked account ids
OPP_ID_M		Masked opp ids
FIRSTDAYOFMONTH		1st day in Calendar month
RENEWAL_SEQUENCE	CATEGORICAL	Identifies the sequential place of the opportunity in question against all other opportunities for the related account.
CHARGE_MODEL_NAME	CATEGORICAL	Seat vs envelopes limited and unlimited
IS_WEBUPGRADE	CATEGORICAL	Flag identifying Opportunities of order type = Upgrade from Web
IS_EXPANSION	CATEGORICAL	Flag identifying Opportunities of order type = Expansion
SALES_SEGMENT	CATEGORICAL	4 sales segment, - Ent, Majors, Mid-Market and SMB
REGION	CATEGORICAL	Sales Region
MRR_BAND_M	CATEGORICAL	Mrr group into band and masked. Band range from 500 to 50K
ACCOUNT_HAS_TCSM	CATEGORICAL	Technical customer service manager. When assigned can be important to determine if the customer consumption/ engagement improved
ACCOUNT_HAS_CSM_FLAG	CATEGORICAL	Customer service manager. When assigned can be important to determine if the customer consumption/ engagement improved
ACCOUNT_HAS_CSM_SPECIALIST_FLAG	CATEGORICAL	Specialist customer service manager. When assigned can be important to determine if the customer consumption/ engagement improved
ACCOUNT_HAS_AM	CATEGORICAL	Flag = 1 if Client Services Executive is assigned
ACCOUNT_SERVICES_BUNDLE	CATEGORICAL	Indicated what service or a combination of services are attached to the opportunity
POST_FY21_ORDER_START_FLAG	CATEGORICAL	indicated if the first order of this account was after feb 2020 - covid opp
DAYS_TO_SEND	NUMERICAL	Is the number of days it took to send the first envelope for an account
PRICE_PER_ENV_TO_REGION_RATE	NUMERICAL	the price per envelope normalized based on region mrr
MONTHLY_PS_COMPLETED_FLAG	CATEGORICAL	flag that indicates if professional service was completed
MONTHLY_SSO_COMPLETED_FLAG	CATEGORICAL	flag that indicates if single sign on service was completed
MONTHLY_AC_COMPLETED_FLAG	CATEGORICAL	flag that indicates adoption consulting was completed
MONTHLY_CUST_DSU_COMPLETED_FLAG	CATEGORICAL	flag indicates if Paid DSU service completed. This gives us information on customer engagement
FREE_DSU_ENGAGEMENT_FLAG	CATEGORICAL	flag indicates if free DSU online was accessed, completed or enrolled. This gives us information on customer engagement
DCS_ENGAGEMENT_FLAG	CATEGORICAL	flag indicated if DCS was open or clickthrough
OPPORTUNITY_ALLOWANCE_PRIORITY_BASED	NUMERICAL	Gives the term allowance from Zuora if it is greater than 2, else will give opportunity allowance + addon value
ADD_ON_ENV_CNT	NUMERICAL	Gives the number of addon count for an opportunity
MONTHLY_OPPORTUNITY_ALLOWANCE_ADDON_FLAG	CATEGORICAL	flag to indicate if there was addon added
MONTHLY_ACTUALS_SENT	NUMERICAL	number of envelopes sent monthly
MONTHLY_SUCCESSFUL_TRANSACTION_RATE	NUMERICAL	indicates if the monthtly env sent was complete
PERFORMANCE_CONSUMPTION_BY_TERM_ELAPSED	NUMERICAL	indicates the performance of account wrt to term elapsed
MONTHLY_TEMPLATES_USED_PCT	NUMERICAL	Normalized template feature used by each account on a monthly basis by monthly allowance priority based
MONTHLY_CUSTOMER_INT_USAGE_PCT	NUMERICAL	Normalized cutomer integrator feature used by each account on a monthly basis by monthly allowance priority based
MONTHLY_PARTNER_INT_USAGE	NUMERICAL	Partner integrator feature used for each account in the last 30 days from current date
MONTHLY_DSBUILT_INT_USAGE_PCT	NUMERICAL	Normalized dsbuilt feature used by each account on a monthly basis by monthly allowance priority based
MONTHLY_DSBUILT_INT_USAGE	NUMERICAL	dsbuilt feature used by each account on a monthly basis by monthly allowance priority based
MONTHLY_DSAPP_INT_USAGE	NUMERICAL	dsapp feature used by each account on a monthly basis by monthly allowance priority based
MONTHLY_DSAPP_INT_USAGE_PCT	NUMERICAL	Normalized dsapp feature used by each account on a monthly basis by monthly allowance priority based
ADV_FEATURE_USAGE_INTERM	CATEGORICAL	Flag to indicated if any advanced feature was used by the account
SUPPORT_VOLUME_INTERM	NUMERICAL	If a support ticket was created
PREV_RENEWAL_TYPE	CATEGORICAL	For 1st renewal assigned NEWCOHORT, remaining based on the renewal
ACCOUNT_PRODUCT_TYPE	CATEGORICAL	esign vs multi product
CONTRACT_LENGTH	CATEGORICAL	Term length categorized as 1, 2,3 and 3+ years
INDUSTRY	CATEGORICAL	Sales Industry
MONTH_IN_TERM		Based on the term length the month in which the account is
MONTH_IN_YEAR		Calendar month in year
REMAINING_MONTHS_IN_TERM		The number of months left in the contract
TARGET_RENEWAL_OUTCOME		The outcome of account based on delta normalized value - UPSELL, FLAT, CHURN - PARTIAL, CHURN - FULL

  
"""
few_shot_examples="""
<<Examples to follow:>>
Question: Help me calculate the total monthly actual sent.
Thought 1: I need to calculate the total of montly actual sent.  
Action 1: Query[SELECT SUM(MONTHLY_ACTUALS_SENT) FROM account_usage]
Observation 1: 735978
Thought 2: Result came back as 735978
Action 4: Answer[The montly actuals sent is 735978]
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

system_message="""
You are a smart AI assistant to help answer churn analysis questions by querying data from Microsoft SQL Server Database and visualizing data with plotly. 
In the examples below, questions are broken down into one or several  parts to be analyzed and eventually to answer the main question.
The action after each thought can be a data query and data visualization code or it can be final answer. 
"""

openai.api_type = "azure"
openai.api_key = ""  # SET YOUR OWN API KEY HERE
openai.api_base = "https://.openai.azure.com/" # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="chatgpt"
database="DocuSignOpenAI"
dbserver=".database.windows.net"
db_user=""
db_password= ""
analyzer = AnalyzeGPT(tables_structure, system_message, few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a  question on churn")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)