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



a. Login to Azure Portal and open the "Cloud Shell"

b. Clone the respository "https://github.com/microsoft/OpenAIWorkshop.git"

c. Go to scenarios/natural_language_query folder

d. Open the "create-sql.ps1" script and provide the location, resourcegrGroup, server,database,login, password, subscription, tenantid information. Save the file

e. Run the "create-sql.ps1" script and it will create the SQL server with sample database


   
## Step 2: Deploy Azure Function App

a. Login to Azure Portal and open the "Cloud Shell"

b. Go to scenarios/natural_language_query/azurefunc/ folder

d. Open the "create-func.ps1" script and provide the location, resourcegrGroup, storageaccountname, and functionname.Save the file

e. Run the "create-func.ps1" script and it will create the function App with function

f. Once function is created, go to function and cick "Configuration" under Settings

g. Open the "config-func.txt" in the scenarios/natural_language_query/ folder and provide your GPT_ENGINE, OPEN_API_KEY, OPENAI_RESOURCE_ENDPOINT, SQL_DB_NAME, and SQL_SERVER_NAME values

h. Under "Application Settings", click on "Advance edit" and copy the updated ""config-func.txt" values in the editor. DO not delete the existing contents in "Advance edit", just add the updated ""config-func.txt" values

<img width="919" alt="image" src="https://user-images.githubusercontent.com/50298139/223740863-166c6bba-bc5e-44ab-969b-cf5d1e77c6c1.png">


i. Save the changes

j. Under Settings in function click on "Identity" , under "System assigned" set the "Status" to "On", Save the changes

<img width="929" alt="image" src="https://user-images.githubusercontent.com/50298139/223740677-b00bcefb-8dbf-4a49-b67b-2254d43669be.png">

h. Go to SQL server, under "settings", click "Azure Active Directory" and click "Set admin", on right side provide the name of function app which you have provided in point b. Add the name and click 

i. Copy the updated values and click OK

<img width="947" alt="image" src="https://user-images.githubusercontent.com/50298139/223740181-eaa03b0e-e654-49b9-86ce-b77e763a66ad.png">


**Note : SQL_DB_NAME, and SQL_SERVER_NAME should be same names which you created in step 1**





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


 Click on the flows and edit the Power Automate Flow and update Azure Function Url. Make sure that flow is **turned on**

<img width="928" alt="image" src="https://user-images.githubusercontent.com/50298139/222619285-09a545a9-73c3-4dd9-a1b6-c9cc2ca7e440.png">




<img width="492" alt="image" src="https://user-images.githubusercontent.com/50298139/222619362-c786a8f7-a070-4846-837b-6b083b82f6c6.png">
## Step 5. Test

Click on the play button on the top right corner in the PowerApps Portal to launch PowerApp and click submit
. 
Feel free to make changes to the PowerApps UI to add your own functionality and UI layout. You can explore expanding PowerAutomate flow to connect to other APIs to provide useful reference links to augment the response returned from OpenAI.


