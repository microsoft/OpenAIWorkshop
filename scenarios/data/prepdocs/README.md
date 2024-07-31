# How to load documents into Azure AI Search Index

## Pre-reqs
- [Create Azure Storage account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal)

- [Create Azure AI Search Service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal)

- [Create Document Intelligence Service](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/create-document-intelligence-resource?view=doc-intel-4.0.0)

- [Create Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal)

## Step One

**Edit the command_run.txt file**
Add the following to the environment varaibles:
- searchkey - Your AI Search key
- openaikey - Azure OpenAI key
- formrecognizerkey - Document intelligence key
- storagekey - Azure storage account key
- AZURE_STORAGE_ACCOUNT - Azure storage account. Example: "kirbyadlsgen2"
- AZURE_STORAGE_CONTAINER_SOURCE - The name of the storage account container where you store the data.
- AZURE_STORAGE_CONTAINER - The name of the storage account container to upload documents to.
- AZURE_SEARCH_SERVICE - Name of your AI search service. Example: "myaisearch"
- AZURE_OPENAI_SERVICE - The name of your Azure OpenAI service. Example: "aoaiwestus"
- AZURE_OPENAI_EMB_DEPLOYMENT - The name of your embedding deployment. Example: "text-embedding-ada-002"
- AZURE_FORMRECOGNIZER_RESOURCE_GROUP - Resource Group name for document intelligence. Example: "OpenAI"
- AZURE_FORMRECOGNIZER_SERVICE - The name of your document intelligence service. Example: "formreckirby"
- AZURE_TENANT_ID - Go to Entra\Azure AD and get the tenant ID
- AZURE_SEARCH_ADMIN_KEY - Admin key for your AI Search Service
- AZURE_SEARCH_INDEX_NAME - New or existing index name for AI Search. If it doesn't exist, one will be created. 

## Step Two
In order to install all the requirements run the following
    `pip install -r requirements.txt`

## Step Three
In VS Code open a Windows terminal 
Copy and paste the entire contents of the command_run.txt file into the command terminal

*** Note that the new version of the program prepdocs.py_mp.py supports parallel loading. You should use a machine with multiple cores to take advantage of multi-core processing. Good and easy options would be: a compute instance in Azure ML. The F series has 20-96 cores machine there. You can also use github workspace.