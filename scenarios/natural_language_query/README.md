# Build Open AI Application on Power App to allow users to use natural language question on top of SQL data
### Summary.

This scenario allows use cases to use Open AI as an intelligent agent to get business promprs in natural language from end users and generating SQL queries from the prompts as:

Generating SQL queries from the natural language 
Giving direct answer to questions about specific product, service and process by excuting the query from SQL database.




This implementation scenario focuses on building a Nautual Language to query from business questions and genarte the queries for database retrieval 
### Architecture Diagram
<img width="925" alt="image" src="https://user-images.githubusercontent.com/50298139/222232002-cee2d89e-58fb-4436-9bc6-20f085f332d7.png">

### Solution Flow

Step 1: Provide the context information: context information can be provided to system through a form, we are using Power App form, this information is submitted to Azure function

Step 2: Azure function passes the context information to Open AI Engine to convert the user context information to SQL Query

Step 3: Azure Open AI engine converts the user context ask into SQL query and pass the query back to Azure function

Step 4: The genrated SQL query is passed from function to Azure SQL databse 

Step 5: The query is executed on SQL database and results are returned to Azure function

Step 6: The query resuilts are retunrd to end user 

### Deployment
Azure services deployment
1: Setup Azure SQL database with ssample data

2: Deploy Azure Function App

3: Deploy the Open API model on Open AI

3: Depoy the Power App

4: Deploy client Power App

