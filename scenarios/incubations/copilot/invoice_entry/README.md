# Scenario Overview
This scenario demonstrate the use of voice transcription service by Azure Open AI Whisper together with GPT-4 0613 to create a 
copilot for accountant.

- [Watch the demo video](./invoice_voice_copilot.webm)

- You can ask the copilot to create the invoice for you. You need to provide invoice header information and one or multiple line items.
- You can also ask the copilot to query invoices with filter conditions such as due date, amount, vendor etc..

# Installation 
## Open AI setup
Create an Azure OpenAI deployment in an Azure subscription with a GPT-4-0603 deployment and a ada-text-embedding-002 deloyment
## Run the application locally
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/incubations/copilot/invoice_entry```
2. Create a `secrets.env` file under ``invoice_entry`` folder
```
WHISPER_AOAI_ENDPOINT=WHISPER_ENDPOINT_URL
WHISPER_AOAI_KEY=WHISPER_KEY
WHISPER_DEPLOYMENT="NAME_OF_WHISPER_DEPLOYMENT"
AZURE_OPENAI_ENDPOINT="ENDPOINT"
AZURE_OPENAI_API_KEY="YOUR_AZURE_OPENAI_KEY"
AZURE_OPENAI_CHAT_DEPLOYMENT="" #deployment_id of your gpt-4 deployment

```
3. Create a python environment with version from 3.7 and 3.10

    - [Python 3+](https://www.python.org/downloads/)
        - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
        - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`. 
4. Import the requirements.txt `pip install -r requirements.txt`
5. To run the multi-agent copilot from the command line: `streamlit run app.py`

## Deploy the application to Azure 
##To be added







