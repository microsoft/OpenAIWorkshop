
## POWER APP

### Prerequiste

[Azure OpenAI resource](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#prerequisites)


1. Navigate to https://make.powerapps.com/. On **Welcome to Power Apps** select your **Country/Region** click **Get Started**. 

   ![](./images/welcome.png)
    
2. Select **Apps** on the left navigation and click **Import Canvas App**. 

    ![](./images/import-canvas.png)

3. On **Import package** page click on **Upload**.

    ![](./images/upload-importpackage.png)


### Step 2. Deploy client Power App

- click on Apps on the left navigation. 

  <img src="../../documents/media/powerapp.png" width=50% height=50%>


- From the top nav bar, click Import Canvas App and upload the power app zip file from this git repo path. 


  <img src="../../documents/media/importpowerapp.png" width=50% height=50%>


  <img src="../../documents/media/importpowerappzip.png" width=50% height=50%>


- Click on Import to import the package into powerapps environment. 


  <img src="../../documents/media/importpowerappandflow.png" width=50% height=50%>


- This will import the Power App canvas app and the Power Automate Flow into the workspace. 


  <img src="../../documents/media/openaisummarizationflow.png" width=50% height=50%>


- Click on the flows and edit the Power Automate Flow

  <img src="../../documents/media/editflow.png" width=50% height=50%>


- Edit the Power Automate Flow HTTP step with your own Azure OpenAI API [key and endpoint](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/quickstart?pivots=rest-api#retrieve-key-and-endpoint)


  <img src="../../documents/media/flowchangeapikey.png" width=50% height=50%>


- Save the flow and make sure that flow is turned on


### Step 2. Test

- run the App by clicking on the App

  <img src="../../documents/media/runpowerapp.png" width=50% height=50%>
