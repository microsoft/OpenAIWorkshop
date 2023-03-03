# Build Open AI Application on Power App to allow users to use natural language question on top of SQL data
### Summary.

This scenario allows users to use Open AI as an intelligent agent to get business questions prompts from end users and generating SQL queries from the prompts.This implementation scenario focuses on building a Nautual Language to query from business questions and genarte the queries for database retrieval 
### Architecture Diagram
<img width="693" alt="image" src="https://user-images.githubusercontent.com/50298139/222239136-9149247e-b6e9-4b8b-8519-be7c8f3723b4.png">


### Solution Flow

Step 1: Context information is provided to system through a Power App form, this information is submitted to Azure function

Step 2: Azure Open AI engine converts the user context prompt to SQL query and passes the query to Azure function

Step 3: Azure function passes the context information to Open AI Engine to convert the user context information prompt to SQL Query

Step 4: The Azure function passes the genrated SQL query text and executes the query on Azure SQL databse 

Step 5: The query is executed on SQL database and results are returned to Azure function

Step 6: Azure function returns the results to end user 
### Azure services deployment
## Step 1: SQL Server Deployment



Create SQL server with Sample database,please provide the database name as **"oaisqldemo"**.Follow the links in below step to create the SQL database in the resourcegroup where you wil like to host your databbase and openai service  https://www.sqlshack.com/create-an-azure-sql-database-with-built-in-sample-data/
<img width="905" alt="image" src="https://user-images.githubusercontent.com/50298139/222620998-e30223f8-b44a-4524-a80a-3aba68ce30ee.png">


Please click "Set admin" and **provide your functionname** which you created as in step 2 
<img width="674" alt="image" src="https://user-images.githubusercontent.com/50298139/222620873-0cb5201d-d587-41aa-b58d-d0b2bf73785e.png">



   
## Step 2: Deploy Azure Function App

First create a function App 


<img width="395" alt="image" src="https://user-images.githubusercontent.com/50298139/222745311-e0659d19-2c4f-4a06-b563-c6cbcb06e115.png">




Clone the repository to VS Code and open the cloned folder in VS Code, right click the "natural_language_query" and click "Deploy to Function App". Please ensure VS Code is linked to your Azure subscription and Azure function where you have deployed the function app in previous step

<img width="284" alt="image" src="https://user-images.githubusercontent.com/50298139/222796264-4d70c370-75bc-475b-b3ac-5a63338f790d.png">

Update the function configuration in Azure Function App configuration blade, add below parameters from your Open AI API deployment parameters 


           
Configuration Blade

<img width="876" alt="image" src="https://user-images.githubusercontent.com/50298139/222794270-8a16e80d-a108-4d7c-8039-7d85a71711af.png">

Once function is deployed, please test on the function from function console in azure portal

<img width="920" alt="image" src="https://user-images.githubusercontent.com/50298139/222808013-01227e88-98a0-47ac-a42f-268b64654da2.png">




## Step 3. Deploy client Power App

From the powerapp folder, download "NLQuery PowerApp Export.zip" powerapp package. This has a powerapp and powerautomate template app pre-built.
Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. 

![](../../documents/media/powerapps1.png)


From the top nav bar, click Import Canvas App and upload the Semantic-Search-App-Template_20230303012916.zip file from this git repo path. 


![](../../documents/media/powerapps2.png)





Click on Import to import the package into powerapps environment. This will import the Power App canvas app and Power Automate Flow into the workspace. 





<img width="1003" alt="image" src="https://user-images.githubusercontent.com/50298139/222625951-3bfc11be-7f34-4efc-94fd-112c9d5c8c2d.png">

<img width="929" alt="image" src="https://user-images.githubusercontent.com/50298139/222617513-10bf28ae-a2d7-4211-a702-a951098e3c3c.png">


<img width="926" alt="image" src="https://user-images.githubusercontent.com/50298139/222618019-49eab211-1c77-474c-a3aa-8f377df26255.png">

This will import the Power App canvas app and Semantic-Search Power Automate Flow into the workspace.


<img width="746" alt="image" src="https://user-images.githubusercontent.com/50298139/222619006-e9eaa507-836b-4ba7-bf1f-d78e0d84479d.png">


 Click on the flows and edit the Power Automate Flow and update Azure Function Url. 

<img width="928" alt="image" src="https://user-images.githubusercontent.com/50298139/222619285-09a545a9-73c3-4dd9-a1b6-c9cc2ca7e440.png">




<img width="492" alt="image" src="https://user-images.githubusercontent.com/50298139/222619362-c786a8f7-a070-4846-837b-6b083b82f6c6.png">
## Step 5. Test

Click on the play button on the top right corner in the PowerApps Portal to launch PowerApp and click submit
. 
Feel free to make changes to the PowerApps UI to add your own functionality and UI layout. You can explore expanding PowerAutomate flow to connect to other APIs to provide useful reference links to augment the response returned from OpenAI.


