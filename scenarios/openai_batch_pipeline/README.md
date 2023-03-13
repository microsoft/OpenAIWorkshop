# Build an Open AI Pipeline to Ingest Batch Data, Perform Intelligent Operations, and Analyze in Synapse
# Summary

This scenario allows uses OpenAI to summarize and analyze customer service call logs for the ficticious company, Contoso. The data is ingested into a blob storage account, and then processed by an Azure Function. The Azure Function will return the customer sentiment, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 
---

# Table of Contents
- [Build an Open AI Pipeline to Ingest Batch Data, Perform Intelligent Operations, and Analyze in Synapse](#build-an-open-ai-pipeline-to-ingest-batch-data-perform-intelligent-operations-and-analyze-in-synapse)
- [Summary](#summary)
- [Table of Contents](#table-of-contents)
- [Architecture Diagram](#architecture-diagram)
- [Deployment](#deployment)
    - [Step 1. Blob storage and Azure Function app deployment](#step-1-blob-storage-and-azure-function-app-deployment)
    - [Step 2. Ingest Data to Storage created in step 1](#step-2-ingest-data-to-storage-created-in-step-1)
        - [a. Launch Azure Cloud Shell](#a-launch-azure-cloud-shell)
        - [b. In the Cloud Shell run below commands:](#b-in-the-cloud-shell-run-below-commands)
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

---

## Step 2. Ingest Data to Storage created in step 1

### a. Launch Azure Cloud Shell
<img width="870" alt="image" src="https://user-images.githubusercontent.com/123749010/224067489-e2c44741-f154-4a98-82bd-544299cbfbbf.png">

### A filled out template would look like this:
![](../../documents/media/batch_template_filled_out.png)

After clicking the blue **Review** **+** **create** button, wait to make certain the deployment passes the validation check and there are no errors or missing fields. Click **Create** to deploy the template; it will take approximately 2 or 3 minutes to fully deploy. Successful deployment will look like this:

![](../../documents/media/batch_template_success.png)
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

### a. Create the Synapse Resource in your Resource Group
Navitate to the Resource Group created in Step 1 and click **Create**, located in the top-left. This will bring you to the Marketplace. Search for **Synapse** and select **Azure Synapse Analytics**. Click **Create** in the lower-lefthand.

![](../../documents/media/batch_createbutton.png)

Fill out the template (sample filled out version below) - you will need to provide a **Workspace name**. If you have existing Data Lake Storage Gen2 or file system accounts, you can select them here. If you do not have existing accounts, you can create new ones. Click **Review + Create** in the bottom left.

![](../../documents/media/batch_create_synapsews.png)

### b. Create the Synapse SQL Pool
Once the Synapse Workspace has been created, navigate to the Synapse Workspace in the Azure portal, and click to **Open** the **Azure Synapse Studio** in the **Getting started** section. This will open a new browswer window with the Synapse Studio.

Once in the Synapse Studio, on the left-hand side, click the tool-box icon (with the wrench sign) to open the **Manage** Options. At the top of the newly opened menu bar, under the **Analytics pools** section, click **SQL pools**. Then click **New** in the top-left.

![](../../documents/media/batch_synapse_pool.png)
> **Please note:** You will need to supply a name for the Synapse SQL Pool. Accept all other defaults.

Accept the defaults and press **Review + Create** in the bottom left, then **Create** once it passes validation. Once the SQL Pool has been created, click **Go to resource** in the top-left.

 - After the SQL Pool is created, create the target table by running the following query:
    ```bash 
        CREATE TABLE [dbo].[cs_detail]
    (
    interaction_summary varchar(8000),
    sentiment varchar(500),
    topic varchar(500),
    product varchar(500),
    filename varchar(500)
    )
    ```
    ![](../../documents/media/target.png)

    - Create linked services for source and target. For this case you need to create one for the json files in data lake and other for Synapse SQL DB.

    ![](../../documents/media/linkedservices.png)

 - Create a dataflow to ingest the data from datalake into Synapse SQL. Provide the connection details (linked services created in the above step) for source and sink. 

    ![](../../documents/media/dataflow.png)

    - Create a pipeline to trigger the ingestion.

    ![](../../documents/media/pipeline.png)

    - Trigger the run and query the target table after successful completion of the pipeline.

    ![](../../documents/media/pipelinerun.png)


## Step 4. Test

Now that the data is in the target table it is available for usage by running SQL queries against it, or connecting PowerBI and creating visualizations. The Azure Function is running as well, so try uploading some of the transcript files to the generated_documents folder in your container and see how the function processes it and creates a new file in the cleansed_documents file.

Here is a query to get started:

 ```bash 
    SELECT sentiment, count(*)
    FROM [dbo].[cs_detail]
    GROUP BY sentiment
    ORDER BY count(*) desc      
 ```

