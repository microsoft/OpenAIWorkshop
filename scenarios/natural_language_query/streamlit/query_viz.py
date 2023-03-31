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
openai.api_key = os.getEnv("OPENAIKEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getEnv("API_BASE") # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2022-12-01"

openai.api_version = "2023-03-15-preview" 

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class AnalyzeGPT():
    max_response_tokens = 1250
    token_limit= 4096
    gpt_deployment="gpt-35-turbo"
    tables_structure="""
    - Fact.Order(Order_Key(PK),City_Key(FK),Customer_Key(FK),Stock_Item_Key(FK),Order_Date_Key(FK),Picked_Date_Key(FK),Salesperson_Key(FK),Picker_Key(FK),WWI_Order_ID,WWI_Backorder_ID,Description,Package,Quantity,Unit_Price,Tax_Rate,Total_Excluding_Tax,Tax_Amount,Total_Including_Tax,Lineage_Key)
    - Fact.Purchase(Purchase_Key(PK),Date_Key(FK),Supplier_Key(FK),Stock_Item_Key(FK),WWI_Purchase_Order_ID,Ordered_Outers,Ordered_Quantity,Received_Outers,Package,Is_Order_Finalized,Lineage_Key)
    - Fact.Sale(Sale_Key(PK),City_Key(FK),Customer_Key(FK),Bill_To_Customer_Key(FK),Stock_Item_Key(FK),Invoice_Date_Key(FK),Delivery_Date_Key(FK),Salesperson_Key(FK),WWI_Invoice_ID,Description,Package,Quantity,Unit_Price,Tax_Rate,Total_Excluding_Tax,Tax_Amount,Profit,Total_Including_Tax,Total_Dry_Items,Total_Chiller_Items,Lineage_Key)
    - Dimension.City(City_Key(PK),WWI_City_ID,City,State_Province,Country,Continent,Sales_Territory,Region,Subregion,Location,Latest_Recorded_Population,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Customer(Customer_Key(PK),WWI_Customer_ID,Customer,Bill_To_Customer,Category,Buying_Group,Primary_Contact,Postal_Code,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Date(Date(PK),Day_Number,Day,Month,Short_Month,Calendar_Month_Number,Calendar_Month_Label,Calendar_Year,Calendar_Year_Label,Fiscal_Month_Number,Fiscal_Month_Label,Fiscal_Year,Fiscal_Year_Label,ISO_Week_Number)
    - Dimension.Stock_Item(Stock_Item_Key(PK),WWI_Stock_Item_ID,Stock_Item,Color,Selling_Package,Buying_Package,Brand,Size,Lead_Time_Days,Quantity_Per_Outer,Is_Chiller_Stock,Barcode,Tax_Rate,Unit_Price,Recommended_Retail_Price,Typical_Weight_Per_Unit,Photo,Valid_From,Valid_To,Lineage_Key)
    - Dimension.Supplier(Supplier_Key(PK),WWI_Supplier_ID,Supplier,Category,Primary_Contact,Supplier_Reference,Payment_Days,Postal_Code,Valid_From,Valid_To,Lineage_Key)
"""

    sql_system_message = f"""
 <<Database tables>>:
 {tables_structure}
You are a smart AI assistant to help answer business question by querying data from Microsoft SQL Server Database and visualizing data with plotly. 
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

    python_system_message = """
 You are a helpful assistant who helps write excellent python plotly visualization code.
 When a new business question together with SQL query is asked by the user, you help by generating the python code.
 Task: Generate code for a python function that uses plotly library to best visualize the data from the SQL query.
  - The function name is visualize_result and it accepts df_sql_result as input. df_sql_result is the pandas dataframe that contains the result of the SQL query.
  - The function visualize_result decide on the best form of plotly visualization for the business question and convert the graph object with to_html(full_html=False) and return.
"""
    python_system_message =  {"role": "system", "content": python_system_message}
    sql_system_message =  {"role": "system", "content": sql_system_message}


        
    def execute_sql_query(self,query,database="WideWorldImportersDW",server="oaisqldemo.database.windows.net"):
        #logging.info('Python HTTP trigger function processed a request.')
        
        driver="{ODBC Driver 17 for SQL Server}"
        db_token = ''
        connection_string = 'DRIVER='+driver+';SERVER='+server+';DATABASE='+database
        username = os.getEnv("SQLUSERNAME") 
        password = os.getEnv("SQLPASSWORD") 
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
        with open(f"{file_name}.py", "w") as file:
            file.write(python_code)
        graph = imp.load_source("graph", f"{file_name}.py")
        fig = graph.visualize_data(observation_df)
        st.plotly_chart(fig)
        os.remove(f"{file_name}.py")

        

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
                
                







    
