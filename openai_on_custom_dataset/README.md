# Using Azure OpenAI on custom dataset
### This solution allows OpenAI agent to answer questions on a custom dataset.
### Architecture Diagram
![OpenAI on custom dataset](../documents/media/openaioncustomdataset.png)
From the user's query, the solution uses two-stage information retrieval to retrieve the content that best matches the user query. 
In stage 1, full text search in Azure Cognitive Search is used to retrieve a number of relevant documents. In stage 2, the search result is applied with pretrained NLP model and embedding search to further narrow down the the most relavant content. The content is used by orchestrator service to form a prompt to OpenAI deployment of LLM. The OpenAI service returns result which is then sent to Power App client application.
### Deployment
### Ingest data
### Test

