# Build Open AI pipeline to ingest batch data, perform intelligent operations and insert into Synapse
### Summary

This scenario allows uses OpenAI to summarize and analyze customer service call logs for the ficticious company, Contoso. The data is ingested into a blob storage account, and then processed by an Azure Function. The Azure Function will return the customer sentiment, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 

### Architecture Diagram

![](../../documents/media/batcharch.png)

Call logs are uploaded to a designated location in Blob Storage. This upload will trigger the Azure Function which utilzies the [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service/) for summarization, sentiment analysis, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 

### Deployment

## Step 1. Blob storage and Azure Function app deployment
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FOpenAIWorkshop%2Fnicole-dev%2Fscenarios%2Fopenai_batch_pipeline%2Fdeploy%2Fazuredeploy.json)

**Please Note:** Azure Open AI must be provisioned with one of the models being deployed. 

**OPENAI_API_KEY** and **OPENAI_RESOURCE_ENDPOINT** can be found by naviagting to Azure OpenAI service in the Azure portal 

<img width="821" alt="image" src="https://user-images.githubusercontent.com/123749010/224167487-4f9e5365-b8d7-4678-bcfd-2948ac570df3.png">

**OPENAI_MODEL_NAME** can be found in the Azure OpenAI studio under the deplyment section

<img width="707" alt="image" src="https://user-images.githubusercontent.com/123749010/224169094-7ae29ad6-713c-4c53-a58f-b8f8a07556ff.png">

## Step 2. Ingest Data to Storage created in step 1

a. Launch Azure Cloud Shell
<img width="870" alt="image" src="https://user-images.githubusercontent.com/123749010/224067489-e2c44741-f154-4a98-82bd-544299cbfbbf.png">

b. In the Cloud Shell run below commands:

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
    conda activate document-generation
    pip install -r reqs.txt
```

```bash 
    python upload_docs.py --conn_string "<CONNECTION_STRING>"
```
**Please Note:** CONNECTION_STRING can be found by navigating to storage account  created in Step 1 in the Azure portal. 

<img width="839" alt="image" src="https://user-images.githubusercontent.com/123749010/224180217-274f74cd-1a95-4b42-8b4e-96ae9d9a5a99.png">


## Step 3. Set up Synapse Workspace
- Create a Synapse workspace, provide the details and click 'Review + Create'

    ![](../../documents/media/synapse_create.png)

    - Under SQL pools –> click New and create new dedicated SQL pool. This will take few minutes.

    ![](../../documents/media/synapsesqlpool.png)

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

