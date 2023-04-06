import streamlit as st
import random
import pandas as pd
import sys
from analyze import AnalyzeGPT
import openai

tables_structure="""
The table account_usage has following structure
Feature	Data Type	Description
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
MONTH_IN_TERM	CATEGORICAL	Based on the term length the month in which the account is
MONTH_IN_YEAR	CATEGORICAL	Calendar month in year
REMAINING_MONTHS_IN_TERM	NUMERICAL	The number of months left in the contract
TARGET_RENEWAL_OUTCOME	CATEGORICAL	The outcome of account based on delta normalized value - UPSELL, FLAT, CHURN - PARTIAL, CHURN - FULL

"""
few_shot_examples="""
<<Examples to follow:>>
Question: What's the region with largest percentage in number of accounts?
Thought 1: I need to build query to caculate the percentage of accounts count per each region and retrieve the top one.  
Action 1: Query[SELECT TOP 1  \nREGION,  \nCOUNT(DISTINCT ACCOUNTID_M) AS ACCOUNT_COUNT,  \n(CAST(COUNT(DISTINCT ACCOUNTID_M) AS FLOAT) / (SELECT COUNT(DISTINCT ACCOUNTID_M) FROM account_usage) * 100.0) AS PERCENTAGE_OF_TOTAL  \nFROM   \naccount_usage  GROUP BY   \nREGION  \nORDER BY   \nPERCENTAGE_OF_TOTAL DESC  \n]
Observation 1: REGION	ACCOUNT_COUNT	PERCENTAGE_OF_TOTAL
NULL	2406	66.2809917355372
Thought 2: Based on the query results, the top region in terms of the count of accounts is "NULL" 
Action 2: Answer[The region with most accounts is NULL representing 66.28% of total accounts count]
Question: List top 3 accounts in terms of MONTHLY_ACTUALS_SENT
Thought 1: I need to build query to retrieve information for the question. Finally, I need to visualize data using bar chart to show the comparision among accounts.
Action 1: Query[SELECT TOP 3   \nACCOUNTID_M,   \nSUM(MONTHLY_ACTUALS_SENT) AS TOTAL_ENVELOPES_SENT  \nFROM   \naccount_usage  \nGROUP BY   \nACCOUNTID_M  \nORDER BY   \nTOTAL_ENVELOPES_SENT DESC ], Python[```\nimport plotly.express as px\n\ndef visualize_data(sql_result_df):\n    fig=px.line(sql_result_df, x='TOTAL_ENVELOPES_SENT', y='nACCOUNTID_M', title='Top 3 Accounts')\n    return fig\n```]
Observation 1: ACCOUNTID_M	TOTAL_ENVELOPES_SENT
634c13f0f4a1b7d83b10e6f915e98da9813a7ec82aa83cac7ceb5d53e1f06f31	171128
749604e079f245a05774ec95a144afeb907f4a88cca1f3dc7c6c750ed9631300	133419
6c1d4fdde6d9ab32e2f451a5702de0ffb3fe5311ee462a82e543f65fa6c5903d	85292
Thought 2: The result answers the question
Action 2: Answer[The result is provided]

"""

system_message="""
You are a smart AI assistant to help answer accounts analysis questions by querying data from Microsoft SQL Server Database and provide code to visualize data with plotly. 
Only use the table and columns in provided in the <<Database structure>> to write queries. Use Microsoft SQL Server compliant query syntax.
Some useful background for you.
- Use coefficient variation to evaluate seasonality
"""

openai.api_type = "azure"
openai.api_key = "6b134b679f0e4a5b90925cdca6eaf391"  # SET YOUR OWN API KEY HERE
openai.api_base = "https://azopenaidemo.openai.azure.com/" # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="chatgpt"
gpt_deployment="gpt-35-turbo"
database="DocuSignOpenAI"
dbserver="oaisqldemo.database.windows.net"
db_user="oaireaderuser"
db_password= "Oaiworkshop@password123"
analyzer = AnalyzeGPT(tables_structure, system_message, few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a  question on churn")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)