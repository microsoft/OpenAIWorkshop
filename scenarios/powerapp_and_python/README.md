# Build Open AI application with Power App and Python

## Scenario summary:
This scenario allows use cases to use Open AI from Power App and as well from Python application via OpenAI Python SDK. 

## POWER APP


### Step 1. Deploy client Power App

- Navigate to https://make.powerapps.com/ and click on Apps on the left navigation. 

  <img src="../../documents/media/powerapp.png" width=50% height=50%>


- From the top nav bar, click Import Canvas App and upload the OpenAI-Playground_20230302010547.zip file from this git repo path. 


  <img src="../../documents/media/importpowerapp.png" width=50% height=50%>


  <img src="../../documents/media/importpowerappzip.png" width=50% height=50%>


- Click on Import to import the package into powerapps environment. 


  <img src="../../documents/media/importpowerappandflow.png" width=50% height=50%>


- This will import the Power App canvas app and Openaisummarization Power Automate Flow into the workspace. 


  <img src="../../documents/media/openaisummarizationflow.png" width=50% height=50%>


- Edit the Power Automate Flow with your own Azure OpenAI API key and endpoint.


  <img src="../../documents/media/flowchangeapikey.png" width=50% height=50%>


### Step 2. Test

- Click on the play button on the top right corner in the PowerApps Portal to launch PowerApp. 


## PYTHON SDK

### Step 1. Install required python packages

- In your command line run "pip install -r requirements.txt" to install openai python package 


### Step 2. Open openaipython.py file

- Put your own OpenAI API key and OpenAI endpoint in this file