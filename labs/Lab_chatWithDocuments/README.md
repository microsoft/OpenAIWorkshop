# Using Azure OpenAI on custom dataset
### Scenario summary:

This scenario allows use cases to use Open AI as an intelligent agent to answer questions from end users or assist them using knowledge of a proprietary corpus and domain.
Applications can be:
- Giving direct answer to questions about specific product, service and process based on a knowledge corpus that can be updated frequently. This is an alternative to classic search where the result are just documents with relevant information to the question. Think of this as Bing Chat on proprietary data.
- Giving recommendation & assistance: based on information that can be implicitly gathered about the user, formulate useful content for the user's purpose. For example, a travel website may utilize users' personal information, past posts and transaction history to personalize recommendations when users need to be helped with creating next trip idea/itinerary

Regardless of the application scenario, the solution flow is:
- Step 1 prepare the context information: context information can be retrieved from proprietary knowledge corpus and other systems based on the user's query and user's information. The retrieval mechanism can be a semantic search engine to retrieve right content for unstructured data corpus or SQL query in case of structured dataset.
- Step 2 fomulate prompt to Open AI: from the context and depending on the goal of user, formulate GPT prompt to get the final response to end user. For example, if it's knowlege retrieval vs. recommendation

This implementation scenario focuses on building a knowledge retrieval chatbot application on top of unstructured data corpus but the same design can be used for recommendation & generative scenarios.

### Architecture Diagram
![Alt text](Images/lab2_image1_architecture.png)


From the user's query, the solution uses two-stage information retrieval to retrieve the content that best matches the user query.
In stage 1, full text search in Azure Cognitive Search is used to retrieve a number of relevant documents. In stage 2, these documents are then used by orchestrator service to form a prompt and sent to OpenAI deployment endpoint of LLM. The OpenAI service returns result which is then sent to Power App client application.

### Pre-reqs:

- Microsoft.Search and Microsoft.BotService Resource provider needs to be [registered](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types#register-resource-provider) in the Azure Subscription.​

- [PostMan Client](https://www.postman.com/downloads/)  installed on your laptop. ​

- [Azure Cloud Shell](https://shell.azure.com/)​

- [.Net Core 3.1](https://dotnet.microsoft.com/en-us/download/dotnet/3.1) or later​

- Install [Node.js](https://nodejs.org/en/download)

- [Azure Bot Framework Composer​](https://learn.microsoft.com/en-us/composer/install-composer?tabs=windows)

- [Bot Framework Emulator​](https://github.com/Microsoft/BotFramework-Emulator/releases/tag/v4.14.1)

### Deployment


### 2. Deployment script.

The steps are broken into 3 key steps with a few manual steps.
- In the first step, provision Azure Resourcs using Azure Portal UI.
- In the second step, the search-index is configured and executed to create the search index.
- In the third step, a chatbot is developed using Azure Bot Framework Composer. Bot Framework Emulator is used for testing the developed chatbot.

To proceed, please click [here](Script.md).




