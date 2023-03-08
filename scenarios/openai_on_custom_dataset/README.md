# Using Azure OpenAI on custom dataset
### Scenario summary:
This scenario supports use cases to invoke OpenAI as an intelligent agent for the purpose of answering questions from end users or to assist them in applying knowledge from a custom knowledge corpus and domain.
Applications include: 
- Giving direct answers to questions about a specific product, service or process based on a knowledge corpus that can be updated frequently. This is an alternative to classic search where the result includes documents with only relevant information to the question. This can be thought of as using Bing Chat on top of custom data.
- Giving recommendations and assistance based on information that can be implicitly gathered about the user and then formulate useful content for the user's purpose. For example, a travel website may utilize users' personal information, past posts and transaction history to personalize recommendations when users request a sample trip itinerary tailored to a list of requirements.

For both applications mentioned, the solution process flow includes the following:
- **Step 1. Gather Context**: contextual information can be retrieved from knowledge corpuses and other systems based on the user's query and user's information. The retrieval mechanism can be a semantic search engine to retrieve relevant content from an unstructured dataset or a SQL query sourcing from a relational database.
- **Step 2. Formulate Prompt and retrieve response**: for a goal and context supplied by the user, formulate a GPT prompt, invoke the OpenAI service, and display personalized recommendations or knowledge retrieval to the user.

This implementation scenario focuses on building a knowledge retrieval chatbot application on top of an unstructured knowledge corpus but the same design can be used for recommendation & generative scenarios.

### Architecture Diagram
![OpenAI on custom dataset](../../documents/media/AzureCognitiveSearchOpenAIArchitecture.png)
The solution uses a two-stage information retrieval process to retrieve the content that best matches the user query. 
In stage 1, full text search in Azure Cognitive Search is used to retrieve a number of relevant documents. In stage 2, the search result is applied with a pretrained NLP model and embedded search is done to further narrow down the the most relevant content. The content is used by orchestrator service to form a prompt and submit  to an Azure OpenAI service deployment supporting Large Language Models (LLM). The Azure OpenAI service returns a result which is then displayed to the user via a Power Apps client application.
### Deployment


### Prerequisites

* Azure Open AI already provisioned and a __text-davinci-003__ model is deployed. If another deployment model must be used, then manual adjustments will need to be made in following lab instructions.
* [PostMan Client Installed](https://www.postman.com/downloads/) for testing HTTP requests to Azure Functions. The Azure Portal can also be used to interact with and test Azure Functions REST API connectivity.
* Azure Cloud Shell is recommended if Option A is chosen for programmatic configuration via Python, as it includes preinstalled dependencies. 
    * Conda is recommended if local laptops must be used as a pip install could interfere with an existing python deployment.



## 1. Deploy Azure Services

Deploy Azure Resources, namely an Azure Function App for abstracting access to OpenAI and Search APIs, Azure Search Service, and an Azure Form Recognizer resource.

Here are the SKUs used by the provisioned Azure Resources:

- Azure Function App - Consumption Plan
- Azure Cognitive Search - Standard (supports semantic search)
- Azure Form Recognizer - Standard (supports analysis of a 500 page document)
- Azure Storage - General Purpose v1 (supports Azure Function App and sample document upload)


The deployed Azure Function App includes code to invoke a Power Automate Flow, which uses a REST API request to a specified OpenAI service provisioned within an Azure subscription.


[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FOpenAIWorkshop%2Fanildwa-dev%2Fscenarios%2Fopenai_on_custom_dataset%2Fdeploy%2Fazure-deploy.json)



- Step 1: Set up Azure Cognitive Search and prepare data

    As part of the data preperation step, to work best with OpenAI, the documents are chunked into smaller units (20 lines) and stored as individual documents in the search index. The chunking steps can be achieved with the search-indexer python script provided and executed in this lab. If you do not prefer to use the Azure Command Line Interface (CLI) in the Azure Portal to execute the automated python script, proceed to the Optional Manual Approach.
    To make it easy for the labs, the sample document has already been chunked and provided in the repo. 

    *   Enable Semantic Search on Azure Portal. Navigate to the Semantic Search blade and select the Free plan. 
    
        ![](../../documents/media/enable-semantic-search.png)
        
        * __Note__: Before moving forward with the instructions, choose one of the following 2 options to configure and perform Search Indexing. Option A outlines a programmatic approach using Python within the Azure Command Line Interface (CLI) in Azure Cloud Shell. Option B outlines how to use the Azure Portal for a GUI-based experience. If a GUI-based Portal approach is preferred, skip to Option B (above the next screenshot titled "Import data").

    *   __Option A (Programmatic Approach)__: Create a Search Index, Semantic Configuration and Index a few documents using an automated script. The script can be run multiple times without any side effects.
        Run the below commands to configure the python environment. If running in the [Azure Command Line Interface (CLI)](https://portal.azure.com/#cloudshell/), the conda installation lines (3-4) below can be removed, and the backslashes can be updated to be forwardslashes. <repo> should be substituted with the repo URL (e.g. https://github.com/microsoft/OpenAIWorkshop.git).

                        
            git clone <repo>
            cd OpenAIWorkshop/scenarios/openai_on_custom_dataset
            conda create env -n openaiworkshop python=3.9
            conda activate openaiworkshop
            pip install -r ./orchestrator/requirements.txt


        *   Update Azure Search, Open AI endpoints, AFR Endpoint and API Keys in the secrets.env. 
            Rename secrets.rename to secrets.env. (This is recommended to prevent secrets from leaking into external environments.)
            The secrets.env should be placed in the ingest folder with the existing python script file search-indexer.py.
            The endpoints below needs to have the trailing '/' at end for the search-indexer to run correctly.
        
            After moving and renaming the secrets.rename file to secrets.env in the openai_on_custom_dataset/ingest directory, use the "code filename" command to alter the contents of the file below with a text editor. See the Notes section below if necessary to retrieve the associated values.
     
            AZSEARCH_EP="https://<>.search.windows.net/"
            AZSEARCH_KEY=""
            AFR_ENDPOINT="https://westus2.api.cognitive.microsoft.com/"
            AFR_API_KEY=""
            INDEX_NAME="azure-ml-docs"
        
            __Note__:
        *   Ensure that the <> in __AZSEARCH_EP__ is substituted with the value for your Search Service resource available on the __Overview__ blade in the Portal.
        *   Substitute __AZSEARCH_KEY__ with the __Query key__ value available on the __Keys__ blade for the Search Service in the Portal.
        *   Replace the __AFR_API_KEY__ with the available on the __App keys__ blade for the Azure Function App resource in the Portal. Either _master or default key values can be used.
        *   Replace the region prefix in the __AFR_ENDPOINT__ value (e.g. westus2 to eastus) if the Azure Function was deployed in a region other than West US 2.


        *   The document processing, chunking, indexing can all be scripted using any preferred language, with Python demonstrated here. Run the below script to create a search index, add semantic configuration and populate sample documents from the Azure Docs extracts used by this lab. 
        The search indexer chunks a sample PDF document (500 pages) which is downloaded from Azure Docs and chunks each page into 20 lines. Each chunk is created as a new search document in the index. The PDF document processing is achieved using the Azure Form Recognizer service. 
     

            cd .\scenarios\openai_on_custom_dataset\ingest\
            python .\search-indexer.py
            

    *   __Option B (Azure Portal approach)__:  If you prefer to not use the programmatic approach outlined above in Option A, visit the [Azure Portal](https://portal.azure.com) and complete the storage account and Azure Search configuration as described below.
        
        Import data

        - Navigate to the resource group used by the lab deployment. Once selected, find the Storage account resource auto-provisioned by the template used in step 1. Click on the __Storage Acccount__ name, click on the __Blob service__ link, and create a blob container.  
        - Extract the data files in the .scenarios/data/data-files.zip folder and update this folder to the blob container using the [Azure Portal UI](https://portal.azure.com/#cloudshell/). The data-files.zip contains the Azure ML sample PDF document chunked as individual files per page.  
        - Import data to Azure Search as shown below. Choose the blob container and provide the blob-folder name to continue. 

            ![](../../documents/media/search1.png)
        - In the Customize Target Index window, use id as the Azure Document Key and text as the Searchable Field. 
        - As a result, with this configuration, the chunked sample will be indexed

## Step 2: Configure Orchestration with Azure Function Apps

    Review the Azure Function App's __Configuration__ blade within the Settings section for the resource in the Portal. Double check that the Application Settings mentioned below are available by name, and briefly review the Hidden value to ensure that they match expected values. The OPENAI_API_KEY and OPENAI_RESOURCE_ENDPOINT values should be auto-populated with the values you looked up in the Portal and provided earlier in the lab.

            {
                "name": "GPT_ENGINE",
                "value": "text-davinci-003",
                "slotSetting": false
            },
            {
                "name": "INDEX_NAME",
                "value": "azure-aml-docs",
                "slotSetting": false
            },
            {
                "name": "OPENAI_API_KEY",
                "value": "<>",
                "slotSetting": false
            },
            {
                "name": "OPENAI_RESOURCE_ENDPOINT",
                "value": "https://<>.openai.azure.com/",
                "slotSetting": false
            },
            {
                "name": "SEMANTIC_CONFIG",
                "value": "semantic-config",
                "slotSetting": false
            }

## Step 3. Test Azure service deployment via Postman

Launch Postman and test the Azure Function to make sure it returns results. The num_search_result query parameter can be altered to retrieve more or less search results. Notice the query parameter num_search_result in the screenshot below. A parameter named "code" also needs to be supplied to match the one of your Function's __App key__ values (either the _master or default values in the __App key__ blade of the resource in the Portal.


![](../../documents/media/postman.png)

## Step 4. Deploy client application via Power Apps

From the powerapp folder of the openai_on_custom_dataset folder of this repo, download the Semantic-Search-App-Template_20230303012916.zip powerapp package. This has a prebuilt Canvas app including Power App and Power Automate components.
Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. 

![](../../documents/media/powerapps1.png)


From the top nav bar, click Import Canvas App and upload the downloaded Semantic-Search-App-Template_20230303012916.zip file. 


![](../../documents/media/powerapps2.png)


![](../../documents/media/powerapps3.png)


Click on Import to import the package into Power Apps environment. 


![](../../documents/media/powerapps4.png)


This will import the Power App canvas app and Semantic-Search Power Automate Flow into the workspace. 



![](../../documents/media/powerapps7.png)


The Power Automate Flow needs to be enabled. Locate the Flows pane, find the imported Flow by name, and Turn on the Flow by click on the __More commands (...)__ icon.

![](../../documents/media/powerapps8.png)

Edit the Power Automate Flow and update Azure Function URL in the HTTP activity. Optionally, the num_search_result query parameter can be altered.



![](../../documents/media/powerapps5.png)

## Step 5. Launch and Test End-to-End via Power Apps

Click on the play button on the top right corner in the Power Apps Portal to launch the Power App.
Select an FAQ from dropdown and click Search. Also experiment with custom search terms. This returns answers powered by Open AI GPT-3 Models. 
Feel free to make changes to the PowerApps UI to add your own functionality and UI layout. You can explore expanding Power Automate flow to connect to other APIs to provide useful reference links to augment the response returned from OpenAI.


