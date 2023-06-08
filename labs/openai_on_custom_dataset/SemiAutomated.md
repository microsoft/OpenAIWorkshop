# Semi Automated Script

### Prerequisites

* Contributor permission is required in the Azure subscription.
* Microsoft.Search Resource provider needs to be registered in the Azure Subscription. 
* [PostMan Client Installed](https://www.postman.com/downloads/) for testing Azure Functions. Azure portal can also be used to test Azure Function App.  
* Azure Cloud Shell is recommended as it comes with preinstalled dependencies. 
* Azure Open AI already provisioned and text-davinci-003 model is deployed. The model deployment name is required in the Azure Deployment step below.  
* [Azure Bot Framework Composer](https://learn.microsoft.com/en-us/composer/install-composer?tabs=windows#install-and-run-composer) is installed in local computer.
* [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator/releases/tag/v4.14.1) installed in local computer. 



## 1. Azure services deployment

Deploy Azure Resources namely - Azure Function App to host facade for OpenAI and Search APIs, Azure Search Service and a Azure Form Recognizer resource.

Here are the SKUs that are needed for the Azure Resources:

- Azure Function App - Consumption Plan
- Azure Cognitive Search - Standard (To support semantic search)
- Azure Forms Recognizer - Standard (To support analyzing 500 page document)
- Azure Storage - general purpose V1 (Needed for Azure Function App and uploading sample documents)


The Azure Function App also deploys the function code needed for powerapps automate flow. 

(control+click) to launch in new tab.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FOpenAIWorkshop%2Fmain%2Fscenarios%2Fopenai_on_custom_dataset%2Fdeploy%2Fazure-deploy.json) 



## 2. Setup Azure Cognitive Search and prepare data

As part of data preperation step, to work in Open AI, the documents are chunked into smaller units(20 lines) and stored as individual documents in the search index. The chunking steps can be achieved with a python script below. 
To make it easy for the labs, the sample document has already been chunked and provided in the repo. 

* Enable Semantic Search on Azure Portal. Navigate to Semantic Search blade and select Free plan. 
    
    ![](../../documents/media/enable-semantic-search.png)

*   Create Search Index, Sematic Configuration and Index a few documents using automated script. The script can be run multiple times without any side effects.
    
    Open Cloud Shell by clicking cloud shell icon on the upper right corner of the Azure portal and select PowerShell. Create a Fileshare if it prompts, to save all the files copied through the cloud shell.

    -----Cloud Shell Image-----
    
    Run the below commands from cloud shell to conifgure python environment. 

        
        git clone https://github.com/Microsoft-USEduAzure/OpenAIWorkshop.git
        
        cd OpenAIWorkshop/labs/Lab_2_bot_chatWithDocuments 
        
        pip install -r ./orchestrator/requirements.txt


*   Update Azure Search, Open AI endpoints, AFR Endpoint and API Keys in the secrets.env. 
    Rename secrets.rename to secrets.env. (This is recommended to prevent secrets from leaking into external environments.)
    The secrets.env should be placed in the ingest folder along side the python script file search-indexer.py.
    **The endpoints below needs to have the trailing '/' at end for the search-indexer to run correctly.**

        cd ingest
        
        # open secrets.env using code editor such as code
        # When using code, you can type control+s to save the file and control+q to quit the editor
        
        code secrets.env


    Add the below entries with correct values to secrets.env. Please refer to [this doc](ShowKeysandSecrets.md) to retrieve API Keys and Urls.

        AZSEARCH_EP="https://<YOUR Search Service Name>.search.windows.net/"
        AZSEARCH_KEY="<YOUR Search Service API Key>"
        AFR_ENDPOINT="<YOUR Azure Form Recognizer Service API EndPoint>"
        AFR_API_KEY="<YOUR Azure Form Recognizer API Key>"
        INDEX_NAME="azure-ml-docs"
        FILE_URL="https://github.com/Microsoft-USEduAzure/OpenAIWorkshop/raw/main/labs\Lab_2_bot_chatWithDocuments\Data\azure-machine-learning-2-500.pdf"
        LOCAL_FOLDER_PATH=""

*   The document processing, chunking, indexing can all be scripted using any preferred language. 
    This repo uses Python. Run the below script to create search index, add semantic configuration and populate few sample documents from Azure doc. 
    The search indexer chunks a sample pdf document(500 pages) which is downloaded from azure docs and chunks each page into 20 lines. Each chunk is created as a new seach doc in the index. The pdf document processing is achieved using Azure Form Recognizer service. 
    
        cd OpenAIWorkshop/labs/Lab_2_bot_chatWithDocuments/ingest
        python search-indexer.py
        

## 3. Test Azure Function App service deployment

Please refer to [this doc](ShowKeysandSecrets.md) to retrieve Function App Url and code.


* Launch Postman and test the Azure Function to make sure it is returning results. The num_search_result query parameter can be altered to limit the search results. Notice the query parameter num_search_result in the screen shot below. **num_search_result** is a mandatory query parameter.


    ![](../../documents/media/postman.png)


## 4. Build Chatbot 

- Create an Azure Bot resource: 
    The Azure Bot resource provides the infrastructure that allows a bot to access secured resources. It also allows the user to communicate with the bot via several channels such as Web Chat.
    1. Go to the [Azure portal](https://portal.azure.com/)
    2. In the right pane, select Create a resource.
    3. In the search box enter bot, then press Enter.
    4. Select the Azure Bot card.
    5. Select Create.
    6. Enter the required values.
    7. Select Review + create.
    8. If the validation passes, select Create. You should see the Azure Bot and the related key vault resources listed in the resource group you selected.
    9. Select Open in Composer.

    The Composer application opens. It the application isn't installed, you'll be asked to install it before you can proceed with the next steps.

        1. In the pop-up window, select Create a new bot.
        2. Select Open.

    
- Create a bot in Azure Bot Composer:
    1. Open Composer.
    2. Select Create New (+) on the homepage.
    3. Under C#, select Empty Bot and click next.
    4. Provide a name to your bot (e.g.- OpenAIBot)
    5. Select Runtime type as "Azure Web App".
    6. Select a location in your loal computer where bot files will be stored. 
    7. Click on create. Wait untill the bot is created.
    8. Click on "Unknown intent".
    9. 



[Create PowerApp](PowerApp.md)

## 6. Test

Click on the play button on the top right corner in the PowerApps Portal to launch PowerApp.
Select an  FAQ from dropdown and click Search. This is should bring up the answers powered by Open AI GPT-3 Models. 
Feel free to make changes to the PowerApps UI to add your own functionality and UI layout. You can explore expanding PowerAutomate flow to connect to other APIs to provide useful reference links to augment the response returned from OpenAI.
