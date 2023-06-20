# Exercise 1: Build an Open AI Application on Power App to allow users to use natural language questions on top of SQL data
### Summary

This scenario allows users to use Open AI as an intelligent agent to get business question prompts from end users and generate SQL queries from the prompts. This implementation scenario focuses on building a Natural Language to query from business questions and generate the queries for database retrieval.
### Architecture Diagram
![](images/scenario1.01.png)


### Solution Flow

Step 1: Context information is provided to the system through a Power App form, this information is submitted to Azure function.

Step 2: Azure Open AI engine converts the user context prompt to SQL query and passes the query to Azure function.

Step 3: Azure function passes the context information to Open AI Engine to convert the user context information prompt to SQL Query.

Step 4: The Azure function passes the generated SQL query text and executes the query on Azure SQL database. 

Step 5: The query is executed on SQL database and results are returned to Azure function.

Step 6: Azure function returns the results to end user.
### Azure services deployment
   
## Task 1: Deploy Azure OpenAI Model and Configure Azure Function App.

1. In the **Azure portal**, search for **OpenAI** and select **Azure OpenAI**.

   ![](images/openai8.png)

1. On **Cognitive Services | Azure OpenAI** blade, select **openai-<inject key="DeploymentID" enableCopy="false"/>**

   ![](images/openai9.png)

1. In the Azure OpenAI resource pane, click on **Go to Azure OpenAI Studio** it will navaigate to **Azure AI Studio**.

   ![](images/openai11-1.png)

1. In the **Azure AI Studio**, select **Deployments (1)** under Management and click on **+ Create new deployment (2)**. 

   ![](images/openai10-1.2.png)

1. On the Deploy model pop-up, from the drop-down select **text-davinci-003 (1)** for Select a Model, enter deployment name as **demomodel (2)** then click on **Create (3)**. Copy OpenAI Model name into the text file for later use.

   ![](images/openai-model1.png)

1. Click on **+ Create new deployment**, On the Deploy model pop-up, from the drop-down select **gpt-35-turbo (1)** for Select a Model, enter deployment name as **gptmodel (2)** then click on **Create (3)**. Copy OpenAI Model name into the text file for later use.

   ![](images/openai-model2.png)

1. Once the models are deployed, click on **demomodel** from the **Deployments** page.

   ![](images/deployments.png)

1. Next, click on **Edit deployment**.

   ![](images/editdep.png)

1. On the **Edit deployment** pop-up, expand **Advanced options (1)** and scale-down the **Tokens per Minute Rate Limit (thousands) (2)** to **10k** and click **Save and close (3)**.

   ![](images/tokens.png)

1. Navigate back to **Deployments** page, Select **gptmodel** and click on **Edit deployment**.

   ![](images/gpt.png)

1. On the **Edit deployment** pop-up, expand **Advanced options (1)** and scale-down the **Tokens per Minute Rate Limit (thousands) (2)** to **10k** and click **Save and close (3)**.

   ![](images/gptedit.png)

1. Naviagte back to [Azure portal](http://portal.azure.com/), search and select **Azure OpenAI**, from the **Cognitive Services | Azure OpenAI pane**, select the **OpenAI-<inject key="Deployment ID" enableCopy="false"/>**.

1. On **openai-<inject key="DeploymentID" enableCopy="false"/>** blade, select **Keys and Endpoint (1)** under **Resource Management**. Copy **Key 1 (2)** and the **Endpoint (3)** by clicking on copy to clipboard paste it in a text editor such as notepad for later use. 

   ![](images/openai13a.png)

1. Navigate to **openai-<inject key="DeploymentID" enableCopy="false" /></inject>** resource group, and search and select **SQL database**.

   ![](images/database.png)

1. Now, copy the database name paste it in a text editor such as notepad for later use. 

   ![](images/copydb.png)

1. In **openai-<inject key="DeploymentID" enableCopy="false" /></inject>** resource group, search and select **SQL server**.

   ![](images/server.png)

1. Now, copy the **SQL server** name paste it in a text editor such as notepad for later use. 

   ![](images/copyserver.png)

1. Navigate to `C:\labfile\OpenAIWorkshop\scenarios\natural_language_query/azurefunc` folder and open `func-config.txt` file. Provide the Open AI engine, Open AI rest end point, SQL server and SQL database name in the file and copy the content.

      >**Note:** Provide the Model name as **demomodel**.

1. Go to **openai-<inject key="DeploymentID" enableCopy="false" /></inject> (1)** resource group and open **openaifunapp<inject key="DeploymentID" enableCopy="false" /></inject> (2)** function app.

   ![](images/openai3.png)

1. Go to deployed function and click **Configuration** -> **Application Settings** and click on **Advance edit** and copy the **func-config.txt** values in the editor. Do not delete the existing contents in **Advance edit**, add **`,`** after last '}' before ']' and just update **config-func.txt** values following. After updating the values click **OK** and **Save**.
   
   ![](images/openai2.png)
   
   ![](images/openai4.png)

1. Under Settings in function click on **Identity** , under **System assigned** set the **Status** to **On**, Save the changes.

   ![](images/openai5.png)

1. Go to SQL server **openaiserver-<inject key="DeploymentID" enableCopy="false" /></inject>** under the same resource group, under **settings**, click **Azure Active Directory** and click **Set admin**, on right side provide the name of function app **openaifunapp<inject key="DeploymentID" enableCopy="false" /></inject>**. Add the name and click  **Select** and **Save**.

   ![](images/openai6.png)


## Task 2. Test the function App

1. Go to **openai-<inject key="DeploymentID" enableCopy="false" /></inject> (1)** resource group and open **openaifunapp<inject key="DeploymentID" enableCopy="false" /></inject> (2)** function app.

   ![](images/openai3.png)

2. On the left hand side click on **Functions (1)** and click deployed function **NLQuery (2)**.

   ![](images/openai7.png)

3. From NLQuery go to **Code + Test (1)**, then click **Test/Run (2)** select **GET (3)** in **HTTP method** dropdown, click **+ Add parameter** under **Query** and enter **prompt (4)** in the **Name** field and enter **show top 10 products (5)** in the **Value** field. Click **Run (6)**.

   ![](images/code+test.png)

4. The **Output** tab will have the query results and click on **Close** to close the output results.

   ![](images/output.png)
  
   >**Note:** Please press the Run again if the output tab does not print the records


## Task 3. Deploy client Power App

1. Navigate to https://make.powerapps.com/. Select **Apps (1)** on the left navigation and click on **Import Canvas App (2)**. 

    ![](./images/import-canvas-1.png)
    
  >**Note:** Please click on **Start a free Trial** if you get any pop-up stating **You need a Power Apps Plan**.

2. On the **Import package** page click on **Upload**.

    ![](./images/upload-importpackage.png)

3. From the file explorer navigate to `C:\labfile\OpenAIWorkshop\scenarios\natural_language_query` select the **NLQuery PowerApp Export** folder and click on **Open**.

     ![](./images/nql-update.png)

4. Click on **Import** to import the package into the PowerApps environment. This will import the Power App canvas app and Power Automate Flow into the workspace. 

    ![](./images/import-nlpquery.png)

5. Navigate back to **openai-<inject key="DeploymentID" enableCopy="false" /></inject> (1)** resource group and open **openaifunapp<inject key="DeploymentID" enableCopy="false" /></inject> (2)** function app.

   ![](images/openai3.png)

6. Then click on **Functions (1)** and click deployed function **NLQuery (2)**.

   ![](images/openai7.png)

7. On the **NLQuery** function click on **Get Function Url (1)**, from the drop-down menu select **default (function key) (2)** then **Copy (3)** the URL, Click **OK (4)**. Paste the URL in a text editor such as _Notepad_ for later use.

    ![](./images/get-nlquery-url.png)

8. Navigate back on the PowerApps, select the **Flows** Pane and click on **Edit** for **PromptlnputFlow**.

    ![](./images/promptin-flow-1.png)
 
9. Edit the Power Automate Flow and update **Azure Function Url (1)** with the URL you copied earlier and append `prompt=` at the end. Your URL should look like following. Click **Save (2)**.

    ```
    https://openaifunappXXXXXX.azurewebsites.net/api/NLQuery?prompt=
    ```
  
      ![](images/openai-1.png)

10. Got to **Apps** and select the app with the name **NLP Query**. Run the App by clicking on the App.

      ![](images/powerapps8-1.png)

      ![](images/powerapps9-1.png)


## Task 4. Build the Connector App

1. Navigate to https://make.powerapps.com/ and click on **App launcher** on the top left corner and select **Power Automate**.

     ![](images/app-launcher.png)


2.  Click on **Data (1)** and select **Custom Connectors (2)**, click on **+ New custom connector (3)** then click on **Create from blank (4)**. Just keep the screen as it is and move to the next step.

    ![](images/power-automate.png)
   
3. Enter the **Connector name** as `Openai-custom-connector` **(1)** and click on **Continue (2)**. Just keep the screen as is and move to the next step.

      ![](images/openai-custom-connector-1.png)
   
   >**Note:** Please click on **Start Trial** if you get any pop-up to register.
   
4.  From the file explorer navigate to `C:\labfile\OpenAIWorkshop\scenarios\natural_language_query` and open **get-prompt.txt**.

     ![](images/get-prompt.png)

5. We need to update the below values in the file 

      - **host**: **openaifunapp<inject key="DeploymentID" enableCopy="false" /></inject>.azurewebsites.net (1)**
  
      - **paths**:  **/api/NLQuery (2)**
  
      - **operationId**: **Get-Prompt (3)**

      ![](images/get-prompt-edit-1.png)
  
   >**Note:** host and paths are extracted from your function url and can be retrieved from  below screen. Host should not have "Https", please note operationid needs to be unique per powerapps account
 
      
     ![](images/code-test-getfuncurl.png)


6. In the Custom Connector app browser tab, click on **Start trial**. 
   
   ![](images/start-trail-90days.png)
   
7. Click on **Swagger Editor (1)** and copy the updated file contents from **get-prompt.txt** **(2)** and replace with the content in the **Swagger editor(2)**. Click **Create Connector (3)**.

   ![](images/swagger-editor.png)
   
8. Navigate to https://make.powerapps.com and click on **Flows** and select the flow which you imported in the previous task and click **Edit**.

   ![](./images/promptin-flow-1.png)

9. We will update the power automate flow second step after **PowerApps(V2)**, click on **+ (1)** and select **Add an action (2)**.
  
   ![](images/add-action-1.png)
  
10. Select **Custom (1)** and type `Openai-custom-connector` **(2)** in search and select the custom connector which you created previously **(3)**.
  
    ![](images/choose-operation-1.png)

11. The flow will look like the image provided below.
  
     ![](images/top-5.png)
  
12. You need to delete the third step which in your case will be **HTTTP** flow, click on `...` **(1)** next to **HTTP** and click **Delete (2)**.

     ![](images/delete.png)

13. Click the **Parse JSON** step , click inside the **Content (1)** field, click on right side, and select **body (2)**. 
  
     ![](images/content-body-1.png)
  
14. The Control should like the below. Click **Save**.

     ![](images/save.png)

15. On the **Flows** tab, select **PromptlnputFlow (1)**  then click on `...` **(2)** and **turn on (3)** your flow.
   
    ![](images/turn-on-1.png)
   
16. Click on **Flows** and select the flow which you imported in the previous task and click **Edit** then on **Test**.
    
    ![](images/test-flow.png)
    
17. Select **Manually (1)** and **Save & Test (2)**. 

    ![](images/manually-test-1.png)

18. Click on **Continue** for **Run flow**.

    ![](images/run-flow.png)
 
19.  Under **txtPrompt** enter **Run connector App (1)** and click **Run flow (2)**.

     ![](images/txtprompt-1.png)

20. Once you receive **Your flow run successfully started**, click on **Done**. 
   
    ![](images/successfully-run.png)

21. To monitor the run, go to the **Flows** Page and view the recent run history.
   
    ![](images/monitor.png)
   
22. From the **Apps (1)** tab, select the **NLP Query** click `...` **(2)**  then click **Edit (3)**.
   
     ![](images/apps-nlq-1.png)
     
23. Click on **Power Automate**, then click on `...` next to **Logic flows** and click on **Remove from app**.

      ![](images/nlplogic.png)

24. Next, click on **+ Add flow** and select **Promptinputflow**.
  
      ![](images/openai-8.png)
 
 25. Click **Save** on the top right.
 
     ![](images/openai-9.png)
 

## Task 5. Test the Power App

1. Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. Open the **NLP Query** App.

    ![](images/openai-3.png)
    
1. Click on **Submit** to see the products.

    ![](images/powerapps27.png)


