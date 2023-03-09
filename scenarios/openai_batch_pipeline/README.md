# Build Open AI pipeline to ingest batch data, perform intelligent operations and insert into Synapse
### Summary

This scenario allows use cases to use OpenAI to summarize and analyze customer service call logs. 

### Architecture Diagram

![](../../documents/media/batcharch.png)

Call logs are uploaded to a designated location in Blob Storage. This upload will trigger the Azure Function. This function will return the customer sentiment, product offering the conversation was about, the topic of the call, as well as a summary of the call. These results are written into a separate desginated location in the Blob Storage. From there, Synapse Analytics is utilized to pull in the newly cleansed data to create a table that can be queried in order to derive further insights. 

### Deployment

## Step 1. Blob storage and Azure Function app deployment
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FOpenAIWorkshop%2Fnicole-dev%2Fscenarios%2Fopenai_batch_pipeline%2Fdeploy%2Fazuredeploy.json)

**Please Note:** Azure Open AI must be provisioned with one of the models being deployed. 

**OPENAI_API_KEY** and **OPENAI_RESOURCE_ENDPOINT** could be found by naviagting to Azure OpenAI service in the Azure portal 

<img width="821" alt="image" src="https://user-images.githubusercontent.com/123749010/224167487-4f9e5365-b8d7-4678-bcfd-2948ac570df3.png">

**OPENAI_MODEL_NAME** could be found in the Azure OpenAI studio under the deplyment section

<img width="707" alt="image" src="https://user-images.githubusercontent.com/123749010/224169094-7ae29ad6-713c-4c53-a58f-b8f8a07556ff.png">

## Step 2. Ingest Data to Storage created in step 1

a. Launch Azure Cloud Shell
<img width="870" alt="image" src="https://user-images.githubusercontent.com/123749010/224067489-e2c44741-f154-4a98-82bd-544299cbfbbf.png">

b. In the Cloud Shell run below commands
```bash 
    git clone https://github.com/microsoft/OpenAIWorkshop.git
    cd OpenAIWorkshop/scenarios/openai_batch_pipeline/document_generation
    conda env create -f conda.yaml
    conda activate document-generation
```

```bash 
    python upload_docs.py --conn_string <CONNECTION_STRING>
```

## Step 3. Set up Synapse Workspace
- Create a Synapse workspace, provide the details and click 'Review + Create'

    ![](../../documents/media/synapse_create.png)

    - Under SQL pools –> click New and create new dedicated SQL pool. This will take few minutes.

    ![](../../documents/media/synapsesqlpool.png)

 - After the SQL Pool is created, create the target table by running the following query:
    ```bash 
        CREATE TABLE [dbo].[cs_detail]
    (
        interaction_summary varchar(2000),
        sentiment varchar(50),
        topic varchar(50),
        product varchar(50),
        filename varchar(100),
        load_date date
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

Now that the data is in the target table it is available for usage by running SQL queries against it, or connecting PowerBI and creating visualizations.

