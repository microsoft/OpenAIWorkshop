# AUTOMATE YOUR MAILBOX RESPONSES

## Objective

In this lab you will lean how to use OpenAI to help answer common IT questions sent to help desk mailboxes

 <img src="../../documents/images/lab-1-workflow.png" width=50% >

## Summary

You will need to deploy 2 logic apps. The first logic app reads incoming email of an outlook mailbox; the second logic app calls OpenAI for anwers to the questions and sends a response.

<img src="../../documents/images/lab-1-architecture.png" height=30%>

## Step 1. Signin to Azure Portal

Go to https://portal.azure.com and enter your credentials

## Step 2. Deploy first logic app - email-techsupport-integration

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FMicrosoft-USEduAzure%2FOpenAIWorkshop%2Fmaster%2Flabs%2FLab_1_no_code_low_code_chat_gpt%2Fscripts%2Fopen_ai_integration%2Ftemplate.json)


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


- Edit the Power Automate Flow HTTP step with your own Azure OpenAI API [key and endpoint](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/quickstart?pivots=rest-api&tabs=command-line#retrieve-key-and-endpoint)


  <img src="../../documents/media/flowchangeapikey.png" width=50% height=50%>


- Save the flow and make sure that flow is turned on


### Step 2. Test

- run the App by clicking on the App

  <img src="../../documents/media/runpowerapp.png" width=50% height=50%>