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

![OpenAI on custom dataset](./images/AzureCognitiveSearchOpenAIArchitecture-1.png)

From the user's query, the solution uses two-stage information retrieval to retrieve the content that best matches the user query. 
In stage 1, full text search in Azure Cognitive Search is used to retrieve a number of relevant documents. In stage 2, the search result is applied with pretrained NLP model and embedding search to further narrow down the the most relavant content. The content is used by orchestrator service to form a prompt to OpenAI deployment of LLM. The OpenAI service returns result which is then sent to Power App client application.

# PowerApp

1. From the LabVM open the **File explorer** and navigate to `C:\labfile\OpenAIWorkshop-main\scenarios\openai_on_custom_dataset\powerapp` observe that the `Semantic-Search-App-Template_20230303012916.zip` powerapp package is already downloded for you. This has a powerapp and powerautomate template app pre-built.

   ![](./images/senamtic-search.png)


2. Navigate to https://make.powerapps.com/ and login using your user credentials. On **Welcome to Power Apps** select your **Country/Region** click **Get Started**. on Apps on the left navigation. 

   * Email/Username: <inject key="AzureAdUserEmail"></inject>
   * Password: <inject key="AzureAdUserPassword"></inject>

   ![](./images/welcome.png)
    
3. Select **Apps** on the left navigation and click **Import Canvas App**. 

    ![](./images/import-canvas.png)

4. On **Import package** page click on **Upload**.

    ![](./images/upload-importpackage.png)
    
5. Navigate to `C:\labfile\OpenAIWorkshop-main\scenarios\openai_on_custom_dataset\powerapp` and select `Semantic-Search-App-Template_20230303012916.zip` folder then click **Open**.

   ![](./images/upload-semantic-search.png)
   
7. Click on **Import** to import the package into powerapps environment.

    ![](./images/package-import.png)

8. Once the import is completed, click on **...** next to **Semantic-Search-Template** and click on **Edit**.

    ![](./images/semantic-search-temp-edit.png)
     

9. Click on **Power Automate** This will import the Power App canvas app and Semantic-Search Power Automate Flow into the workspace. 

    ![](./images/semanti-search-flow.png)

10. To navigate back click on **Back** then click **Leave** .

    ![](./images/exit-powerapp.png)

11. In the **Flows** Pane, click on **Edit**. PowerAutomate Flow needs to be enabled. At this point, the powerapp can be run as is. It connects to a pre-built Azure Function App. 

    ![](./images/flows.png)

6. Edit the Power Automate Flow and update Azure Function Url. Optionaly num_search_result query parameter can be altered.

    ![](./images/flow-img.png)
