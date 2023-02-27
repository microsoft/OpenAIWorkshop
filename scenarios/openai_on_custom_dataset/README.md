# Using Azure OpenAI on custom dataset
### Scenario summary:
This scenario allows use cases to use Open AI as an intelligent agent to answer questions from end users or assist them using knowledge of a proprietary corpus and domain.
Examples can be: 
- Giving direct answer to questions about specific product, service and process based on a knowledge corpus that can be updated frequently. This is an alternative to search where the result is direct & summarized knowledge answer to the question. This is similiar to Bing Chat on proprietary data.
- Giving recommendation & assistance: based on information that can be implicitly gathered about the user, formulate useful content for the user according to a particular purpose. For example, a travel website may utilize user's personal information, past posts, transaction history to tailor the recommendation when user need to be helped with creating next trip idea/itenerary



### Architecture Diagram
![OpenAI on custom dataset](../../documents/media/openaioncustomdataset.png)
From the user's query, the solution uses two-stage information retrieval to retrieve the content that best matches the user query. 
In stage 1, full text search in Azure Cognitive Search is used to retrieve a number of relevant documents. In stage 2, the search result is applied with pretrained NLP model and embedding search to further narrow down the the most relavant content. The content is used by orchestrator service to form a prompt to OpenAI deployment of LLM. The OpenAI service returns result which is then sent to Power App client application.
### Deployment

1. Azure services deployment
- Option 1: One-click automated deployment for Azure services: click on this github workflow to deploy all azure services in one step
- Option 2: manually deploy individual services
    - Azure Cognitive Search
    - Reranking sematic search with Azure ML Online Deployment Endpoint
    - Orchestrator service with Azure Function App
2. Ingest data into Azure Cognitive Search
3. Test Azure service deployment
4. Deploy client Power App
5. Test

