# Build an Open AI Pipeline to Ingest Batch Data, Perform Intelligent Operations, and Analyze in Synapse
# Summary

This scenario allows uses OpenAI to summarize and analyze customer service call logs for the ficticious company, Contoso. The data is ingested into a blob storage account, and then processed by an Azure Function. The Azure Function will return the customer sentiment, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 
---

---
# Table of Contents
- [Build an Open AI Pipeline to Ingest Batch Data, Perform Intelligent Operations, and Analyze in Synapse](#build-an-open-ai-pipeline-to-ingest-batch-data-perform-intelligent-operations-and-analyze-in-synapse)
- [Summary](#summary)
- [Table of Contents](#table-of-contents)
- [Architecture Diagram](#architecture-diagram)
- [Deployment](#deployment)
    - [Step 1. Blob storage and Azure Function app deployment](#step-1-blob-storage-and-azure-function-app-deployment)
    - [Step 2. Ingest Data to Storage created in step 1](#step-2-ingest-data-to-storage-created-in-step-1)
    - [Step 3. Set up Synapse Workspace](#step-3-set-up-synapse-workspace)
        - [a. Launch Azure Cloud Shell](#a-launch-azure-cloud-shell)
        - [b. In the Cloud Shell run below commands:](#b-in-the-cloud-shell-run-below-commands)
        - [c. Create Target SQL Table](#c-create-target-sql-table)
        - [d. Create Source and Target Linked Services](#d-create-source-and-target-linked-services)
        - [e. Create Synapse Data Flow](#e-create-synapse-data-flow)
        - [f. Create Synapse Pipeline](#f-create-synapse-pipeline)
        - [g. Trigger Synapse Pipeline](#g-trigger-synapse-pipeline)
    - [Step 4. Query Results in Our SQL Table](#step-4-query-results-in-our-sql-table)




# Architecture Diagram

![](../../documents/media/batcharch.png)

Call logs are uploaded to a designated location in Blob Storage. This upload will trigger the Azure Function which utilzies the [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service/) for summarization, sentiment analysis, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 

# Deployment

## Step 1. Blob storage and Azure Function app deployment
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FOpenAIWorkshop%2Fnicole-dev%2Fscenarios%2Fopenai_batch_pipeline%2Fdeploy%2Fazuredeploy.json)

>**Please Note:** Azure Open AI must be provisioned with one of the models being deployed. 

You will need to supply entries for 4 fields within the template:
* **OPENAI_API_KEY** - This is the API key for the Azure Open AI service
* **OPENAI_RESOURCE_ENDPOINT** - This is the resource endpoint for the Azure Open AI service
* **OPENAI_MODEL_NAME** - This is the name of the model being deployed
* **Resource group** - This is the resource group that will be created for the deployment (You can create a new one or use an existing one)

**OPENAI_API_KEY** and **OPENAI_RESOURCE_ENDPOINT** can be found by naviagting to Azure OpenAI service in the Azure portal 

<img width="821" alt="image" src="https://user-images.githubusercontent.com/123749010/224167487-4f9e5365-b8d7-4678-bcfd-2948ac570df3.png">

**OPENAI_MODEL_NAME** can be found in the Azure OpenAI studio under the deplyment section

<img width="707" alt="image" src="https://user-images.githubusercontent.com/123749010/224169094-7ae29ad6-713c-4c53-a58f-b8f8a07556ff.png">


### A filled out template would look like this:
![](../../documents/media/batch_template_filled_out.png)

After clicking the blue **Review** **+** **create** button, wait to make certain the deployment passes the validation check and there are no errors or missing fields. Click **Create** to deploy the template; it will take approximately 2 or 3 minutes to fully deploy. Successful deployment will look like this:

![](../../documents/media/batch_template_success.png)
---

## Step 2. Ingest Data to Storage created in step 1

### a. Launch Azure Cloud Shell
<img width="870" alt="image" src="https://user-images.githubusercontent.com/123749010/224067489-e2c44741-f154-4a98-82bd-544299cbfbbf.png">

### b. In the Cloud Shell run below commands:
> **Please Note:** The following commands are issued in Bash; please ensure you are using **Bash** in the Cloud Shell.
```bash 
    wget https://repo.anaconda.com/miniconda/Miniconda3-py39_23.1.0-1-Linux-x86_64.sh 
```

```bash 
    sh Miniconda3-py39_23.1.0-1-Linux-x86_64.sh 
```

Accept the agreement and install on the default path:

![](../../documents/media/cloudshell-accept.png)

**Please Note:** If it asks to run conda init, type yes to confirm. 

```bash 
    export PATH=~/miniconda3/bin:$PATH
```

```bash 
    git clone https://github.com/microsoft/OpenAIWorkshop.git
    cd OpenAIWorkshop/scenarios/openai_batch_pipeline/document_generation
    conda create -n document-creation
    conda activate document-creation
    pip install -r reqs.txt
```
Locate the connection string for the storage account created in Step 1 in the Azure portal and the run the following command:

<img width="839" alt="image" src="https://user-images.githubusercontent.com/123749010/224180217-274f74cd-1a95-4b42-8b4e-96ae9d9a5a99.png">

```bash 
    python upload_docs.py --conn_string "<CONNECTION_STRING>"
```

![](../../documents/media/batch_file_upload2.png)

> **Please Note:** CONNECTION_STRING can be found by navigating to storage account  created in Step 1 in the Azure portal. Running the above command will upload the json files to the storage account and will take a few minutes to complete.

Once you have successfully uploaded the json files to the storage account, you can navigate to the storage account in the Azure portal and verify that the files have been uploaded.

![](../../documents/media/batch_file_upload.png)

---

## Step 3. Set up Synapse Workspace

### **a. Create the Synapse Resource in your Resource Group**
Navitate to the Resource Group created in Step 1 and click **Create**, located in the top-left. This will bring you to the Marketplace. Search for **Synapse** and select **Azure Synapse Analytics**. Click **Create** in the lower-lefthand.

![](../../documents/media/batch_createbutton.png)

Fill out the template (sample filled out version below) - you will need to provide a **Workspace name**. If you have existing Data Lake Storage Gen2 or file system accounts, you can select them here. If you do not have existing accounts, you can create new ones. Click **Review + Create** in the bottom left.

![](../../documents/media/batch_create_synapsews.png)

### **b. Create the Synapse SQL Pool**
Once the Synapse Workspace has been created, navigate to the Synapse Workspace in the Azure portal, and click to **Open** the **Azure Synapse Studio** in the **Getting started** section. This will open a new browswer window with the Synapse Studio.

Once in the Synapse Studio, on the left-hand side, click the tool-box icon (with the wrench sign) to open the **Manage** Options. At the top of the newly opened menu bar, under the **Analytics pools** section, click **SQL pools**. Then click **New** in the top-left.

![](../../documents/media/batch_synapse_pool.png)

> **Please note:** You will need to supply a name for the Synapse SQL Pool. Accept all other defaults.

Accept the defaults and press **Review + Create** in the bottom left, then **Create** once it passes validation. It may take a moment for your SQL Pool to initialize. Once it is completed you will see this:

![](../../documents/media/batch_sqlpoolsuccess.png)

### **c. Create Target SQL Table**

Once the SQL Pool has been created, click into the **Develop** section of the Synapse Studio, click the "**+**" sign in the top-left, and select **SQL script**. This will open a new window with a SQL script editor. 

![](../../documents/media/batch_sqlscript1.png)

> **Please Note:** You will need to change the **Connect to** and **Use database** portions in the SQL editor to point towards the SQL Pool you created in the previous step.

![](../../documents/media/batch_sqlscript2.png)

Copy and paste the following script into the editor and click the **Run** button in the top-left, as shown in the picture above.

```SQL 
CREATE TABLE [dbo].[cs_detail]
(
interaction_summary varchar(8000),
sentiment varchar(500),
topic varchar(500),
product varchar(500),
filename varchar(500)
)
 ```

Finish this step by pressing **Publish all** just above the **Run** button to publish our work thus far.

### **d. Create Source and Target Linked Services**

We'll next need to create two linked services: One for our Source (the JSON files in the Data Lake) and another for the Synapse SQL Database that houses the table we created in the previous step.

Click back into the **Manage** section of the Synapse Studio, and click the **Linked services** option under the **External connections** section. Then click **New** in the top-left.

![](../../documents/media/batch_linkedservices1.png)

Start by creating the Linked Services for the source of our data, the JSON files housed in the ADLS Gen2 storage we created with our initial template. In the search bar that opens after you click **New**, search for **blob** and click on Azure Blob Storage as depicted below:

![](../../documents/media/batch_linkedservices2.png)

You will need to provide a **Name** for your Linked Service. Change the **Authentication type** to *System Assigned Managed Identity*. Then select the subcription you have been working in, finally selecting the **Storage account name** which you created in the initial template and loaded the JSON files into:

![](../../documents/media/batch_linkedservices3.png)

Click the **Create** button in blue on the bottom left of the New linked service window.

Next, we'll create the Linked Service to our Target table in our Synapse SQL Pool. Begin by clicking the **New** button in the *Linked services** section as we did in the step just previously for the Source. This time, however, search for "Synapse" and select **Azure Synapse Analytics**.

![](../../documents/media/batch_linkedservices4.png)

In the *New linked service* window that opens, fill in a **Name** for your target linked service. Select the **Azure subcription** in which you have been working and where you created your Synapse SQL Pool. Select the **Server name** and **Database name** which you created earlier and in which created the target table above. Be certain to change the **Authentication type** to *System Assigned Managed Identity*.

![](../../documents/media/batch_linkedservices5.png)

Once you have created the two Linked Services, be certain to press the **Publish all** button at the top to publish our work and finalize the creation of the linked services. After it is finished, you will see a screen similar to this:

![](../../documents/media/batch_linkedservices6.png)

### **e. Create Synapse Data Flow**

While still within the Synapse Studio, we will now need to create a **Data flow** to ingest our JSON data and write it to our SQL Database. For the purposes of this workshop, this will be a very simple data flow that ingests the data, renames some columns, and writes it back out to the target table. 

First, we'll want to go back to the **Develop** tab, select **"+"**, and then *Data flow**

![](../../documents/media/batch_dataflow1.png)

Once the data flow editor opens, click **Add Source**. A new window will open at the bottom of the screen, select "New" on the **Dataset** row while leaving the other options as default:

![](../../documents/media/batch_dataflow2.png)

A new window should open on the right side of your screen. Next, select **Azure Blob Storage** (it is likely in the top, middle of the window), and then press **Continue**. On the following screen select the **JSON** option as our incoming data is in JSON format. Select the **Linked Service** we just set up in the steps above.

You will need to select the proper **File path** to select the Directory where our JSON files are stored. It should be something to the effect of "workshop-data / cleansed_documents". Click the **OK** button to close the window

![](../../documents/media/batch_dataflow3.png)

![](../../documents/media/batch_dataflow4.png)

Next, we'll need to move to the **Source options** panel and drop-down the **JSON settings** options. We need to change the **Document form** option to the *Array of documents* setting. This allows our flow to read each .json file as a separate entry into our database:

![](../../documents/media/batch_dataflow5.png)

If you have turned on a *data flow debug* session, you can head to the **Data preview** tab and run a preview to check your work thus far:

![](../../documents/media/batch_dataflow6.png)

Next we can add in our **Select** tile and do our minor alteration before writing the data out to the Synapse SQL table. To begin, click the small **+** sign next to our ingestion tile, and choose the Select option:

![](../../documents/media/batch_dataflow7.png)

We can leave all the settings as default.

Next we'll add in our **Sink** tile. This is the step that will write our data out to our Synapse SQL database. Click on the small **+** sign next to our **Select** tile. Scroll all the way to the bottom of the options menu and select the Sink option:

![](../../documents/media/batch_dataflow8.png)

Once the **Sink** tile opens, choose **Inline** for the *Sink type*. Then select **Azure Synapse Analytics** for the *Inline dataset type* and the proper **Linked service** based on the name we assigned in our earlier step.

![](../../documents/media/batch_dataflow9.png)

We will then need to head over to the **Settings** tab and adjust the **Scehma name** and **Table name**. If you utilized the script provided earlier to make the target table, the Schema name is **dbo** and the Table name is **cs_detail**.

![](../../documents/media/batch_dataflow10.png)

Before we finish our work in the data flow, we should preview our data:

![](../../documents/media/batch_dataflow11.png)

Previewing our data reveals we only have 3 columns when we are expecting a total of 5. We have lost our Summary and Sentiment columns. To correct this, let's use our **Select** tile to change the names of our columns to the expected output values:

![](../../documents/media/batch_dataflow12.png)

If we return to our **Sink** tile and **Refresh** our **Data preview** we will now see our expected 5 columns of output:

![](../../documents/media/batch_dataflow13.png)

Once you have reviewed the data and are satisfied that all columns are mapped successfully (you should have 5 columns total, all showing data in a string format), we can press **Publish all** at the top to save our current configuration. A window will open at the right side of the screen - press the blue **Publish** button at the bottom left of it to save your changes.

Your completed and saved Data flow will look something like this:
![](../../documents/media/batch_dataflow14.png)

### **f. Create Synapse Pipeline**

Once we have created our **Data flow** we will need to set up a **Pipeline** to house it. To create a **Pipeline**, navigate to the left-hand menu bar and choose the **In tegration** option (it looks like a pipe). Then click the **+** at the top of the Integrate menu to **Add a new resource** and choose **Pipeline**:

![](../../documents/media/batch_pipeline1.png)

Next, we need to add a **Data flow** to our Pipeline. With your new Pipeline tab open, go to the **Activities** section and search for "data" - selec the **Data flow** acvtivity and drag-and-drop it into your Pipeline:

![](../../documents/media/batch_pipeline2.png)

Under the **Settings** tab of the **Data flow**, select the **Data flow** drop-down menu and select the name of the data flow you created in the previous step. 
Then expand the **Staging** section at the bottom of the settings and utilize the drop-down menu for the **Staging linked service**. Choose the linked service you created earlier (feel free to test the connection). Next, set a**Staging storage folder** at the very bottom. You can copy the names in the picture below or choose your own.

Then click **Publish all** to publish your changes and save your progress.

![](../../documents/media/batch_pipeline3.png)

### **g. Trigger Synapse Pipeline**

Once you have successfully published your work, we need to trigger our pipeline. To do this, just below the tabs at the top of the Studio, there is a *lightning bolt* icon that says **Add trigger**. Click to add trigger and select **Trigger now** to begin a pipeline run.

![](../../documents/media/batch_pipeline4.png)

To look at the pipeline run, navigate to the left-hand side of the screen and choose the **Monitor**  option (looks like a radar screen). Then select the **Pipeline runs** option in the **Integration** section. You will then see this and any other pipeline runs that you have triggered (as shown below). This particular pipeline should take approximately 4 minutes (if you are using the uploaded data for the workshop).

![](../../documents/media/batch_pipeline5.png)

---

## Step 4. Query Results in Our SQL Table

Once you see that your pipeline run above was successful:

![](../../documents/media/batch_pipeline6.png)

Now that the data is in the target table it is available for usage by running SQL queries against it, or connecting PowerBI and creating visualizations. The Azure Function is running as well, so try uploading some of the transcript files to the generated_documents folder in your container and see how the function processes it and creates a new file in the cleansed_documents file.

To query the new data, navigate to the menu on the left-hand side, choose **Develop**. You then either add a new SQL Script or open a previous one and copy the SQL Code below. Then select **Run**. Your query results, if you are using the files uploaded as part of this repository or the workshop, you should see similar results to below.

Here is a query to get started:

 ```sql 
SELECT sentiment, count(*) as "Sum of Sentiment"
FROM [dbo].[cs_detail]
GROUP BY sentiment
ORDER BY count(*) desc     
 ```

![](../../documents/media/batch_synapsesuccessquery.png)

[Back to the Top](#Summary)
---
