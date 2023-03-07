import logging
import azure.functions as func
import openai
from datetime import timedelta
import numpy as np
import pandas as pd
import struct
import os
import pyodbc
import json
import os
GPT_ENGINE = os.getenv("GPT_ENGINE")

openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getenv("OPENAI_RESOURCE_ENDPOINT")  # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2022-06-01-preview"

def run_openai(prompt, engine=GPT_ENGINE):
    """Recognize entities in text using OpenAI's text classification API."""
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        temperature=0,
        max_tokens=2048,
    )
    return response.choices[0].text


def execute_sql_query(query):
    #logging.info('Python HTTP trigger function processed a request.')
    server=os.getenv("SQL_SERVER_NAME")
    database=os.getenv("SQL_DB_NAME")
    
   
    driver="{ODBC Driver 17 for SQL Server}"
    db_token = ''
    connection_string = 'DRIVER='+driver+';SERVER='+server+';DATABASE='+database
    
    #When MSI is enabled
    if os.getenv("MSI_SECRET"):
        logging.info('If block of checking MSI')
        conn = pyodbc.connect(connection_string+';Authentication=ActiveDirectoryMsi')
    
    #Used when run from local
    else:
        SQL_COPT_SS_ACCESS_TOKEN = 1256

        exptoken = b''
        for i in bytes(db_token, "UTF-8"):
            exptoken += bytes({i})
            exptoken += bytes(1)

        tokenstruct = struct.pack("=i", len(exptoken)) + exptoken
        conn = pyodbc.connect(connection_string, attrs_before = { SQL_COPT_SS_ACCESS_TOKEN:tokenstruct })
    
    
    cursor = conn.cursor()
    cursor.execute(query) 
    data =cursor.fetchall()

    cols = []
    for i,_ in enumerate(cursor.description):
        cols.append(cursor.description[i][0])

    result = pd.DataFrame(np.array(data), columns = cols)

    return result.to_html()

def get_sales_sql_query(nlquery):
    return f"""
Given tables [SalesLT].[SalesOrderHeader] with following columns
 [SalesOrderID]
      ,[RevisionNumber]
      ,[OrderDate]
      ,[DueDate]
      ,[ShipDate]
      ,[Status]
      ,[OnlineOrderFlag]
      ,[SalesOrderNumber]
      ,[PurchaseOrderNumber]
      ,[AccountNumber]
      ,[CustomerID]
      ,[ShipToAddressID]
      ,[BillToAddressID]
      ,[ShipMethod]
      ,[CreditCardApprovalCode]
      ,[SubTotal]
      ,[TaxAmt]
      ,[Freight]
      ,[TotalDue]
      ,[Comment]
      ,[rowguid]
      ,[ModifiedDate]
Table [SalesLT].[SalesOrderDetail] with following columns
[SalesOrderID]
      ,[SalesOrderDetailID]
      ,[OrderQty]
      ,[ProductID]
      ,[UnitPrice]
      ,[UnitPriceDiscount]
      ,[LineTotal]
      ,[rowguid]
      ,[ModifiedDate]

Table  [SalesLT].[Product] with following columns
[ProductID]
      ,[Name]
      ,[ProductNumber]
      ,[Color]
      ,[StandardCost]
      ,[ListPrice]
      ,[Size]
      ,[Weight]
      ,[ProductCategoryID]
      ,[ProductModelID]
      ,[SellStartDate]
      ,[SellEndDate]
      ,[DiscontinuedDate]
      ,[ThumbNailPhoto]
      ,[ThumbnailPhotoFileName]
      ,[rowguid]
      ,[ModifiedDate]

Table [SalesLT].[ProductCategory] with following columns
[ProductCategoryID]
      ,[ParentProductCategoryID]
      ,[Name]
      ,[rowguid]
      ,[ModifiedDate]

 Write a SQL server query for following question:
 {nlquery}
    """
def get_query(nlquery):
    return f"""
    generate a query in kusto format for following question {nlquery}. 
    The table's name is anomaly_output with columns: location, car_type, count and timestamp
    """




def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    prompt = req.params.get('prompt')
    if not prompt:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')
    count =0
    result = "I cannot understand question can you try again?"
    sql_query="NA"
    while count <10:
        try:
            #logging.info(count)
            openai_query = get_sales_sql_query(prompt)
            logging.info(openai_query)
            sql_query = run_openai(openai_query)
            logging.info(sql_query)
            result= execute_sql_query(sql_query)
            #logging.info(result)
            break
        except:
            count+=1

    return func.HttpResponse(json.dumps({"data":result, "query":sql_query}))
