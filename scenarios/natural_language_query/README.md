# Build Open AI Application on Power App to allow users to use natural language question on top of SQL data
### Summary.

This scenario allows users to use Open AI as an intelligent agent to get business questions prompts from end users and generating SQL queries from the prompts.This implementation scenario focuses on building a Nautual Language to query from business questions and genarte the queries for database retrieval 
### Architecture Diagram
<img width="693" alt="image" src="https://user-images.githubusercontent.com/50298139/222239136-9149247e-b6e9-4b8b-8519-be7c8f3723b4.png">

### Solution Flow

Step 1: Context information is provided to system through a Power App form, this information is submitted to Azure function

Step 2: Azure function passes the context information to Open AI Engine to convert the user context information prompt to SQL Query

Step 3: Azure Open AI engine converts the user context prompt to SQL query and passes the query to Azure function

Step 4: The Azure function passes the genrated SQL query text and executes the query on Azure SQL databse 

Step 5: The query is executed on SQL database and results are returned to Azure function

Step 6: Azure function returns the results to end user 

### Deployment
Azure services deployment
1: Setup Azure SQL database with sample data

2: Deploy Azure Function App

3: Deploy the Open API model on Open AI service

3: Deploy the Power App

4: Deploy  Power App

