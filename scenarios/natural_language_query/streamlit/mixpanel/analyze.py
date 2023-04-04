import openai
import string
import ast
import pyodbc
from datetime import timedelta
import os
import pandas as pd
import numpy as np
import random
import imp
import re
openai.api_type = "azure"
openai.api_key = "db77747b3587407496f968ac23008831"  # SET YOUR OWN API KEY HERE
openai.api_base = "https://openai002.openai.azure.com/" # SET YOUR RESOURCE ENDPOINT

openai.api_version = "2023-03-15-preview" 

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class AnalyzeGPT():
    max_response_tokens = 1250
    token_limit= 4096
    gpt_deployment="gpt-35-turbo"
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

dbo.step1_cta_events has following unique CTA_EVENT values
Blue View Plan CTA
Red Banner
Upgrade Modal

step1_cta_events contains event logs of top-of-the-funnel actions by user id and account id. After engaging with these events, users will land on the same Pricing and Plan page and go through the checkout process, which are recorded in step2_pnp_events file. 
The order of step2_pnp_events  starts with view upgrade pricng or view signup pricing, then buy now botton click, then 'Checkout: Step - Payment' or 'Checkout 2 (Payment)' or 'Checkout 3 (Payment)', then 'Purchase Click', then 'Account Purchase'.
You can join two data sets using either account id or user id. 


"""

    sql_system_message = f"""
 <<Database tables>>:
 {tables_structure}
You are a smart AI assistant to help answer marketing question by querying data from Microsoft SQL Server Database and visualizing data with plotly. 
In the examples below, you analyze the question,clarify with user if needed to understand it, and translate it into data query and data visualization actions. 
Use only tables and columns listed in <<Database tables>> and use comply with Microsoft SQL Server language specification in writing query.
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
Question: Does 20% customer account for 80% of sales?
Thought 1: I need to determine the total sales generated by the company. 
Action 1: Query[SELECT SUM(Total_Including_Tax) AS Total_Sales FROM Fact.Sale]
Observation 1: 198043439.45
Thought 2: I now need to calculate the total sales for the top 20% of customers.
Action 2: Query[WITH CustomerSales AS ( SELECT c.Customer_Key, SUM(Total_Including_Tax) AS Total_Revenue FROM Fact.Sale s  JOIN Dimension.Customer c ON s.Customer_Key = c.Customer_Key  GROUP BY c.Customer_Key ), TopCustomers AS ( SELECT cs.Customer_Key FROM CustomerSales cs WHERE cs.Total_Revenue >= (SELECT TOP 1 PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY Total_Revenue DESC) OVER () FROM CustomerSales) ) SELECT SUM(s.Total_Including_Tax) AS Top_Revenue FROM Fact.Sale s WHERE s.Customer_Key IN (SELECT Customer_Key FROM TopCustomers)]
Observation 2: 102904875.68
Thought 4: Now I need to divide the sales of top 20% customers by total sales
Action 4: Query[SELECT 102904875.68 / 198043439.45 AS Result ]
Observation 4: 0.51960759702913
Thought 5: Result came back and it is less than 80% so top 20% customers do not account for 80% of sales
Action 5: Answer[No, top 20% customers do not account for 80% of sales]


"""
# Question: Now I want to do that for 2014 but visualize using pie chart
# Thought 2: I just need to change the filter condition to 2014 and change the visualization to pie.
# Action 2: Query[SELECT TOP 20 si.Stock_Item, SUM(s.Quantity) AS Total_Quantity_Sold FROM Fact.Sale s JOIN Dimension.Stock_Item si ON s.Stock_Item_Key = si.Stock_Item_Key JOIN Dimension.Date d ON s.Invoice_Date_Key = d.Date WHERE d.Calendar_Year = 2014 GROUP BY si.Stock_Item ORDER BY Total_Quantity_Sold DESC;], Python[```\nimport plotly.express as px\n\ndef visualize_data(sql_result_df):\n    fig = px.bar(sql_result_df, x=\'Total_Quantity_Sold\', y=\'Stock_Item\', title=\'Top 20 Sold Stock Items in 2014\')\n    return fig\n```]

        
    def execute_sql_query(self,query,database="DocuSignOpenAI",server="oaisqldemo.database.windows.net"):
        #logging.info('Python HTTP trigger function processed a request.')
        
        driver="{ODBC Driver 17 for SQL Server}"
        db_token = ''
        connection_string = 'DRIVER='+driver+';SERVER='+server+';DATABASE='+database
        username = "oaireaderuser"
        password = "Oaiworkshop@password123"
        driver = '{ODBC Driver 17 for SQL Server}' # Update the driver version as per your installation  
        
        # Establish the connection  
        conn = pyodbc.connect('DRIVER=' + driver + ';SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)  

        
        #logging.info(conn)
        cursor = conn.cursor()
        try:
            cursor.execute(query) 
        except Exception as e:
            return str(e)
        data =cursor.fetchall()

        cols = []
        for i,_ in enumerate(cursor.description):
            cols.append(cursor.description[i][0])
        if len(cols)>0:
            result = pd.DataFrame(np.array(data), columns = cols).head(20) #limit to 20
        else:
            result = pd.DataFrame()

        return result
    def visualize(self,python_code, observation_df,st):
        if ('```' in python_code):
            python_code = python_code.split('```')  
            # Extract the content between the first and second delimiter  
            python_code = python_code[1]
            python_code= python_code.strip('python')
        st.code(python_code)  
        N=5
        file_name = ''.join(random.choices(string.ascii_letters, k=N))
        os.makedirs(".tmp", exists_ok=True)
        with open(f".tmp/{file_name}.py", "w") as file:
            file.write(python_code)
        graph = imp.load_source("graph", f".tmp/{file_name}.py")
        fig = graph.visualize_data(observation_df)
        st.plotly_chart(fig)
        os.remove(f".tmp/{file_name}.py")

        

    def run(self, question: str, st) -> any:
        #SQL history contain history of business question and sql query responses from ChatGPT.
        question = {"role":"user", "content":f"Question: {question}"}
        i=1
        history = question
        while True:   
            prompt= [self.sql_system_message] +[history]
            response = openai.ChatCompletion.create(
            engine=self.gpt_deployment, 
            messages = prompt,
            temperature=0,
            max_tokens=self.max_response_tokens,
            stop=f"Observation {i}"
            )
            i+=1
            llm_output = (response['choices'][0]['message']['content'])
            output = llm_output.split("\n")
            for out in output:
                if len(out)>0 and ("Thought" in out or "Observation" in out or "Answer" in out):
                    st.write(out)
            if ("Answer" in llm_output) or ("Query[" not in llm_output):
                print(llm_output)
                print("Final aswer is given or no actionable action is provided, stop")
                break
            sql_query, python_code ="",""
            try:
                sql_query = re.findall(r"Query\[(.*?)\]", llm_output, re.DOTALL)[0].strip()

                python_code = re.findall(r"Python\[(.*?)\]", llm_output, re.DOTALL)[0].strip()
            except:
                pass
            if len(sql_query)>0 or len(python_code)>0:
                st.write(f"Action {i-1}:")
            if len(sql_query)>0:
                st.code(sql_query)
                
                if ('```' in sql_query):
                    sql_query = sql_query.split('```')  
                    # Extract the content between the first and second delimiter  
                    sql_query = sql_query[1]

                observation = self.execute_sql_query(sql_query)
                # if len(observation)>0:
                #     st.write(f"Observation {i}:")
                #     st.write(observation)
                st.write(f"Observation {i-1}:")
                display_text =True
                try:
                    observation_out = observation.to_json() #Query execute successfully
                    if len(python_code)>0:
                        self.visualize(python_code,observation,st)
                        display_text=False

                except:
                    observation_out= str(observation)
                if display_text:
                    st.write(observation)
                new_content =  llm_output + f"Observation {i-1}: {observation_out}"
                new_content= history["content"] +"\n"+new_content
                history["content"] = new_content
                if "ODBC Driver" in observation: #query syntax is not correct, need to retry
                    continue
                
                







    
