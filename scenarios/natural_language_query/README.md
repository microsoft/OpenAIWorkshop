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

a. Launch [Azure Portal](https://portal.azure.com)(control+click) and open Azure Cloud Shell
<img width="870" alt="image" src="https://user-images.githubusercontent.com/123749010/224067489-e2c44741-f154-4a98-82bd-544299cbfbbf.png">


b. In the cloud shell,clone the respository by using the below command
```
git clone https://github.com/microsoft/OpenAIWorkshop.git
```
c. In the cloud shell, navigate to "scenarios/natural_language_query/azurefunc" folder by using the below command
  ```
  cd OpenAIWorkshop/scenarios/natural_language_query/azurefunc
  ```

d. In the cloud shell, run "**create-sql-func.ps1**" script with providing the following parameters **location, resourcegrGroup, sqlserver,sqldatabase,databaseuser, password, subscription, tenantid,storageaccountname and functionname** 
```
.\create-sql-func.ps1  "East US" "resourcegorupname" "sqlservername" "sqldatabasename" "databaseuser" "password" "subscription id" "tenantid" "storageaccountname" "functionappname"
```
**For example**-  .\create-sql-func.ps1 "East US" "natural_language_sql_handson" "sample9871" "sample_db9871" "sample_user" "Test@123" "Use your own subscription id" "Use your own tenant id" "samplestorage9871" "sample_funcApp9871"

**Please note-** Subscription Id could be found by navigating to subscriptions in azure portal
<img width="649" alt="image" src="https://user-images.githubusercontent.com/123749010/224065953-e1a73503-2dbb-49b1-a0ac-c741f17d3f3c.png">


Tenant Id could be found by navigating to subscriptions in azure portal
<img width="563" alt="image" src="https://user-images.githubusercontent.com/123749010/224066885-780a3b61-ef23-46a9-a0a9-212be80040e6.png">
   
## Step 2: Configure Azure Function App


a. Open func-config.txt in scenarios/natural_language_query/azurefunc folder and provide the Open AI engine, Open AI rest end point, SQL server and SQL database name

b. Go to deployed function and cick "Configuration" -> "Application Settings" and click on "Advance edit" and copy the "func-config.txt" values in the editor. DO not delete the existing contents in "Advance edit", just update ""config-func.txt" values before the last line and ']' mark. After copying the values click "OK" and "Save"

<img width="919" alt="image" src="https://user-images.githubusercontent.com/50298139/223740863-166c6bba-bc5e-44ab-969b-cf5d1e77c6c1.png">


b. Under Settings in function click on "Identity" , under "System assigned" set the "Status" to "On", Save the changes

<img width="929" alt="image" src="https://user-images.githubusercontent.com/50298139/223740677-b00bcefb-8dbf-4a49-b67b-2254d43669be.png">

c. Go to SQL server, under "settings", click "Azure Active Directory" and click "Set admin", on right side provide the name of function app which you have provided in point b. Add the name and click  "Select" and "Save"

<img width="947" alt="image" src="https://user-images.githubusercontent.com/50298139/223740181-eaa03b0e-e654-49b9-86ce-b77e763a66ad.png">



## Step 3. Test the function App

a. Go to Function App and click "Functions" and click deployed function "NLQuery"


<img width="1159" alt="image" src="https://user-images.githubusercontent.com/50298139/223866900-d86c34c3-1934-4c6c-987b-f80e87591f6a.png">

b. Click "Code + Test" 

<img width="1139" alt="image" src="https://user-images.githubusercontent.com/50298139/223867081-f7eae62e-2a1f-4c10-817a-d12ddc392d8e.png">

c.  Click Test/Run -> select "GET" in "HTTP method" dropdown, click + next to "Query" and enter "prompt" in Name field and "show top 10 products" in value field. Click "Run"


<img width="1166" alt="image" src="https://user-images.githubusercontent.com/50298139/223867936-97ad6fe2-0d39-4f5b-b305-0ae933cd53b7.png">


d. The "Output" tab will have the query results 


Note : Please press the Run again if the output tab does not print the records

<img width="469" alt="image" src="https://user-images.githubusercontent.com/50298139/223868339-17d32779-4dbd-4ae9-ac27-2b56e0e055a5.png">



## Step 4. Deploy client Power App

a. From scenarios/natural_language_query folder, download "NLQuery PowerApp Export.zip" powerapp package. This has a pre-built powerapp and powerautomate template app.
Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. 

![](../../documents/media/powerapps1.png)


b. From the top navigation bar, click Import Canvas App and upload the "NLQuery PowerApp Export.zip" file . 


![](../../documents/media/powerapps2.png)





c. Click on Import to import the package into powerapps environment. This will import the Power App canvas app and Power Automate Flow into the workspace. 





<img width="1003" alt="image" src="https://user-images.githubusercontent.com/50298139/222625951-3bfc11be-7f34-4efc-94fd-112c9d5c8c2d.png">

<img width="929" alt="image" src="https://user-images.githubusercontent.com/50298139/222617513-10bf28ae-a2d7-4211-a702-a951098e3c3c.png">


<img width="926" alt="image" src="https://user-images.githubusercontent.com/50298139/222618019-49eab211-1c77-474c-a3aa-8f377df26255.png">




 d. Click on the flows and edit the Power Automate Flow and update Azure Function Url. Make sure that flow is **turned on**

<img width="928" alt="image" src="https://user-images.githubusercontent.com/50298139/222619285-09a545a9-73c3-4dd9-a1b6-c9cc2ca7e440.png">

e. Please click the HTTP and provide the function URL in the "URI" field, this function URL can be taken from the "Code + Test" screen -> get function URL tab


<img width="635" alt="image" src="https://user-images.githubusercontent.com/50298139/223873817-38984955-94f1-4f70-8f02-c075ecf87469.png">


<img width="492" alt="image" src="https://user-images.githubusercontent.com/50298139/222619362-c786a8f7-a070-4846-837b-6b083b82f6c6.png">

## Step 5. Test the Power App

a. Navigate to https://make.powerapps.com/ and click on Apps on the left navigation.

b.  Search the App which you deployed in step 4 and and click it 

<img width="767" alt="image" src="https://user-images.githubusercontent.com/50298139/223872433-152f6b03-2a24-4871-a2b6-664ec11f406e.png">


<img width="851" alt="image" src="https://user-images.githubusercontent.com/50298139/223872137-3882ba80-e9d6-4198-a5e4-2ebc0ed485b5.png">




