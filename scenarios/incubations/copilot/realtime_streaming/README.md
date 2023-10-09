## Flight Copilot demo application:
- Retrieve a passenser booking details from CosmosDB
- Check real time updates on flight status (e.g changes due to weather) and policies with data coming from Kafka and indexed with Azure Cognitive Search
- Provide personalized answer for passenser's questions on flight policy, baggage limit etc..
- Help customer to change flight   

You need to create CosmosDB, Kafka cluster and Azure Search.
Please create a secrets.env in this folder and provide details about the services
```
AZURE_OPENAI_ENDPOINT=""
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_EMB_DEPLOYMENT=""
AZURE_OPENAI_CHAT_DEPLOYMENT="" #recommended to use gpt-4
AZURE_SEARCH_SERVICE_ENDPOINT=""
AZURE_SEARCH_INDEX_NAME= #index that contain policy detail
AZURE_SEARCH_ADMIN_KEY=
AZURE_OPENAI_API_VERSION="2023-07-01-preview"
COSMOS_URI=
COSMOS_KEY=
COSMOS_DB_NAME=
COSMOS_CONTAINER_NAME=
USE_AZCS="True" #need to have this so that the search engin use Azure Cognitive Search by default

```


