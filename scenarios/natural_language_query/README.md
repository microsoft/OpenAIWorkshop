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

1. Go to **functionapp<inject key="Deployment ID"></inject>** function app from **openai-<inject key="Deployment ID"></inject>** resource group.

   ![](images/open-func.png)

2. Then click **Functions** and click deployed function **NLQuery**.

   ![](images/nlquery.png)

3. From **NLQuery** go to **Code + Test (1)**, then click **Test/Run (2)** select "GET (3)" in **HTTP method** dropdown, click **+** under to **Query** and enter **prompt (4)** in Name field and **show top 10 products (5)** in value field. Click **Run (6)**.

   ![](images/code+test.png)

4. The **Output** tab will have the query results. 

   ![](images/output.png)
  
   >**Note:** Please press the Run again if the output tab does not print the records

 


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

1. Navigate to https://make.powerapps.com/ and click on .. sign on the top left side, this will open the below , click "Power Auto..."


   ![](images/powerapps10.png)


1.  Click on Data -> “Custom Connectors”, click on “New custom connector” -> ”Create from blank”. Just keep the screen as is and move to point c.


    ![](images/powerapps11.png)

1.  Go to https://github.com/microsoft/OpenAIWorkshop/tree/main/scenarios/natural_language_query and open "get-prompt.txt". We need to update below values in file 


    host : <funcname>.azurewebsites.net
  
    paths :  /api/NLQuery
  
    operationId: Get-Prompt 

    ![](images/powerapps12.png)

  
    >**Note:** host and paths are extracted from your function url and can be retrieved from  below screen. Host should not have "Https", please note operationid needs to be unique per powerapps account

    ![](images/powerapps13.png)


1. In the Custom connector app browser tab , (step b), click on “Swagger Editor” and copy the updated file contents (step c.) in the swagger editor. Click Close to save the Connector


   ![](images/powerapps14.png)
   
1. Navigate to https://make.powerapps.com and click Click on “My Flows” and select the flow which you imported in previous step 4 (d) and click “Edit”

   ![](images/powerapps15.png)

1. We will update the power automate flow second step after PowerApps(V2), click on + and select “Add an action”
  
   ![](images/powerapps16.png)
  
1. Select Custom and type and search for custom connector which we created in step d.
  
   ![](images/powerapps17.png)

1. The flow will look like below
  
   ![](images/powerapps18.png)
  
1. You need to delete the third step which in your case will be “HTTTP” flow, after deleting the third step, click Save

   ![](images/powerapps19.png)

   ![](images/powerapps20.png)
  
1. Click Parse JSON step , click inside "Content" field, click on right side and select “body" . The Control should like the below
  
   ![](images/powerapps21.png)
  
1. click on Test, select Manually and make sure "txtPrompt" in selected in *prompt field, click Run. It will show "Your flow run successfully started. To monitor it, go to the Flow Runs Page." Save the flow

   ![](images/poweraps22.png)


1. go to app which we imported in step 4 and click Edit
  
   ![](images/powerapps23.png)

1. Click on Power Automate,  once Power Automate opens click refresh and click save on right top side. 

   ![](images/powerapps24.png)
  
   ![](images/powerapps25.png)

1. please run the App
  
## Step 5. Test the Power App

1. Navigate to https://make.powerapps.com/ and click on Apps on the left navigation.

1.  Search the App which you deployed in step 4 and and click it 

    ![](images/powerapps26.png)


    ![](images/powerapps27.png)




