# Build Open AI Application on Power App to allow users to use natural language question on top of SQL data
### Summary.

This scenario allows users to use Open AI as an intelligent agent to get business questions prompts from end users and generating SQL queries from the prompts.This implementation scenario focuses on building a Natural Language to query from business questions and generate the queries for database retrieval 
### Architecture Diagram
![](images/scenario1.01.png)


### Solution Flow

Step 1: Context information is provided to system through a Power App form, this information is submitted to Azure function

Step 2: Azure Open AI engine converts the user context prompt to SQL query and passes the query to Azure function

Step 3: Azure function passes the context information to Open AI Engine to convert the user context information prompt to SQL Query

Step 4: The Azure function passes the generated SQL query text and executes the query on Azure SQL database 

Step 5: The query is executed on SQL database and results are returned to Azure function

Step 6: Azure function returns the results to end user 
### Azure services deployment
   
## Step1: Configure Azure Function App

1. Open func-config.txt in scenarios/natural_language_query/azurefunc folder and provide the Open AI engine, Open AI rest end point, SQL server and SQL database name

1. Go to deployed function and click "Configuration" -> "Application Settings" and click on "Advance edit" and copy the "func-config.txt" values in the editor. DO not delete the existing contents in "Advance edit", just update ""config-func.txt" values before the last line and ']' mark. After copying the values click "OK" and "Save"

   ![](images/scenario2.02.png)


1. Under Settings in function click on "Identity" , under "System assigned" set the "Status" to "On", Save the changes

   ![](images/scenario1.03.png)

1. Go to SQL server, under "settings", click "Azure Active Directory" and click "Set admin", on right side provide the name of function app which you have provided in point b. Add the name and click  "Select" and "Save"

   ![](images/scenario1.04.png)



## Step 2. Test the function App

1. Go to Function App and click "Functions" and click deployed function "NLQuery

   ![](images/scenario1.05.png)

1. Click "Code + Test" 

   ![](images/scenario1.06.png)

1. Click Test/Run -> select "GET" in "HTTP method" dropdown, click + next to "Query" and enter "prompt" in Name field and "show top 10 products" in value field. Click "Run"

   ![](images/scenario1.07.png)

1. The "Output" tab will have the query results 


  > **Note:** Please press the Run again if the output tab does not print the records

  ![](images/scenario1.08.png)


## Step 3. Deploy client Power App

1. From scenarios/natural_language_query folder, download "NLQuery PowerApp Export.zip" powerapp package. This has a pre-built powerapp and powerautomate template app.
Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. 

   ![](images/powerapps1.png)


1. From the top navigation bar, click Import Canvas App and upload the "NLQuery PowerApp Export.zip" file . 

   ![](images/powerapps2.png)


1. Click on Import to import the package into powerapps environment. This will import the Power App canvas app and Power Automate Flow into the workspace. 

   ![](images/powerapps3.png)
   
   ![](images/powerapps4.png)
   
   ![](images/powerapps5.png)


1. Click on the flows and edit the Power Automate Flow and update Azure Function Url. Make sure that flow is **turned on**. If you do not have the permissions to "turn on" the flow, please go to **step 5**. In case you are able to turn on the flow, please skip **step 5** and go to **step 6**

   ![](images/powerapps6.png)

1. Please click the HTTP and provide the function URL in the "URI" field, this function URL can be taken from the "Code + Test" screen -> get function URL tab

   ![](images/powerap9.png)

   ![](images/powerapps7.png)

1. Save the flow and run the App by clicking on the App

   ![](images/powerapps8.png)

   ![](images/powerapps9.png)



## Step 4. Build the Connector App (Optional)

a. Navigate to https://make.powerapps.com/ and click on .. sign on the top left side, this will open the below , click "Power Auto..."


![image](https://user-images.githubusercontent.com/50298139/224201114-587353f5-e0a3-4b8e-9647-89d6918c6360.png)


b.  Click on Data -> “Custom Connectors”, click on “New custom connector” -> ”Create from blank”. Just keep the screen as is and move to point c.


![image](https://user-images.githubusercontent.com/50298139/224201199-b14ab884-ed97-4abb-ae9f-c0d464e4658d.png)


c.  Go to https://github.com/microsoft/OpenAIWorkshop/tree/main/scenarios/natural_language_query and open "get-prompt.txt". We need to update below values in file 




host : <funcname>.azurewebsites.net
  
paths :  /api/NLQuery
  
operationId: Get-Prompt 

  ![image](https://user-images.githubusercontent.com/50298139/224388746-ed91b8cb-36ce-4607-a012-e9e801424147.png)

  
Note: **host and paths are extracted from your function url and can be retrieved from  below screen. Host should not have "Https", please note operationid needs to be unique per powerapps account**

  
![image](https://user-images.githubusercontent.com/50298139/224201909-0b54b804-c5aa-45e3-8be2-67b68dec9f78.png)





d.  In the Custom connector app browser tab , (step b), click on “Swagger Editor” and copy the updated file contents (step c.) in the swagger editor. Click Close to save the Connector


  ![image](https://user-images.githubusercontent.com/50298139/224202410-5c18a0c5-c63c-471e-adcb-0d48392509b4.png)


 e.  Navigate to https://make.powerapps.com and click Click on “My Flows” and select the flow which you imported in previous step 4 (d) and click “Edit”

  
 <img width="930" alt="image" src="https://user-images.githubusercontent.com/50298139/224354069-d7dc65a6-c318-4547-83c9-1851136822d2.png">
  

  f. We will update the power automate flow second step after PowerApps(V2), click on + and select “Add an action”
  
![image](https://user-images.githubusercontent.com/50298139/224351924-62f3d1b5-abf3-4694-89c6-a6c9cc1a340e.png)

  
  g. Select Custom and type and search for custom connector which we created in step d.
  
  ![image](https://user-images.githubusercontent.com/50298139/224203067-1972f95e-79ef-4fd2-bf56-d7d516508cd4.png)

  
  h. The flow will look like below
  
  ![image](https://user-images.githubusercontent.com/50298139/224352209-6a95bef2-fb93-4ce9-b906-4e67b0e21fd3.png)

  
  i.You need to delete the third step which in your case will be “HTTTP” flow, after deleting the third step, click Save

![image](https://user-images.githubusercontent.com/50298139/224352282-adef508e-7df1-415b-8509-a6665dd8399b.png)

  
  
  <img width="923" alt="image" src="https://user-images.githubusercontent.com/50298139/224354481-d4e2c3d2-d6a0-4b1d-a1e2-1d98a3301cf4.png">
  
  j. Click Parse JSON step , click inside "Content" field, click on right side and select “body" . The Control should like the below
  
  <img width="932" alt="image" src="https://user-images.githubusercontent.com/50298139/224354658-033eaee3-6579-44c2-a522-aa6b01aefaa9.png">
  
  k. click on Test, select Manually and make sure "txtPrompt" in selected in *prompt field, click Run. It will show "Your flow run successfully started. To monitor it, go to the Flow Runs Page." Save the flow

![image](https://user-images.githubusercontent.com/50298139/224383821-25b8ad3f-668e-4454-a413-aa529606efc5.png)


  l. go to app which we imported in step 4 and click Edit
  
  <img width="780" alt="image" src="https://user-images.githubusercontent.com/50298139/224204881-ae4bace2-f16a-448e-84f9-5b818de6aa67.png">

  m. Click on Power Automate,  once Power Automate opens click refresh and click save on right top side. 

  <img width="697" alt="image" src="https://user-images.githubusercontent.com/50298139/224205091-cecb5d2b-4096-4837-a04b-514bd7b54471.png">
  
  <img width="784" alt="image" src="https://user-images.githubusercontent.com/50298139/224205237-9d7e81cf-526a-4669-a8a1-ec2d61974917.png">



  n. please run the App
  
## Step 6. Test the Power App

a. Navigate to https://make.powerapps.com/ and click on Apps on the left navigation.

b.  Search the App which you deployed in step 4 and and click it 

<img width="767" alt="image" src="https://user-images.githubusercontent.com/50298139/223872433-152f6b03-2a24-4871-a2b6-664ec11f406e.png">


<img width="851" alt="image" src="https://user-images.githubusercontent.com/50298139/223872137-3882ba80-e9d6-4198-a5e4-2ebc0ed485b5.png">




