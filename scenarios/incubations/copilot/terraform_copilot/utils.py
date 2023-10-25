import openai
import dotenv
from pathlib import Path
import datetime
import os
import requests
from audio_recorder_streamlit import audio_recorder
import json
import shutil
from tenacity import retry, wait_random_exponential, stop_after_attempt, stop_after_delay
from fuzzywuzzy import fuzz
import pandas as pd
from io import StringIO
from pandasql import sqldf
import numpy as np

# import API key from .env file
env_path = Path('.') / 'secrets.env'
dotenv.load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
openai.api_version = "2023-07-01-preview"
chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
turbo_deployment = os.getenv("AZURE_OPENAI_TURBO_DEPLOYMENT")
whisper_engine = os.getenv("WHISPER_DEPLOYMENT")

@retry(stop=(stop_after_delay(1) | stop_after_attempt(5)))
def get_gpt_response(message):
    response = openai.ChatCompletion.create(
            deployment_id=turbo_deployment,
            messages=message,
        )
    return response["choices"][0]["message"]['content']

def get_sp(user_request):
    # Read invoices from JSONL file
    system_message1= "You are an expert in terraform. You help prepare a list of input to guide user to write terraform code given the user request. You do this by first draft a terraform code according to user request then from there prepare the list of input you need to get from the user to make the code complete. Then output the list of inputs you need. Do not output terraform code."
    message1 =[{"role": "system", "content": system_message1}, {"role": "user", "content": user_request}]
        
    # terraform_code= get_gpt_response(message1)

    # system_message2= "You are an expert in terraform. Given the following terraform code, if you are to guide a user to generate the code from the begining, list inputs you would need from the user."
    # message2 =[{"role": "system", "content": system_message2}, {"role": "user", "content": terraform_code}]

    return get_gpt_response(message1)


def resolve_vm_sku(vm_name):
    # Load vendors from JSONL file
    with open("data/vm_skus.jsonl", "r") as f:
        vm_skus = [line for line in f]

    # Try to match vendor name exactly
    for vm in vm_skus:
        if vm.lower() == vm_name.lower():
            return f"vm sku \"{vm_name}\" is valid", False

    # Try to match vendor name partially using fuzzy matching
    for vm in vm_skus:
        if fuzz.partial_ratio(vm_name.lower(), vm.lower()) >= 70:
            return vm, True# fuzzy match

    # If no match is found, return "Not found"
    return f"Not found", False



def deploy(terraform_code):
    return "deployment is successful"
    

def validate(**kwargs):
    #for simplicity, we only vm sku
    vm_sku = kwargs["vm_sku"]
    resolved_vm_sku, fuzzy_match = resolve_vm_sku(vm_sku)
    if fuzzy_match:
        return f"vm_sku name \"{vm_sku}\" not found. Did you mean \"{resolved_vm_sku}\"?"
    elif resolved_vm_sku == "Not found":
        return f"vm sku \"{vm_sku}\" not found."
    return "Entered information is valid"
def create_invoice(**kwargs):
    return f"Invoice {kwargs['invoice_number']} created successfully"
PERSONA = """
You an AI assistant helping a developer writing teraform code.
When user ask you to help with writing terraform code, you will need to retrieve the standard procedure specific to the user request using get_sp function.
Follow the standard procedure to interact with user to get needed inputs. Use the tenant and subscription that user is currently logged-in.
Then use the validate function to validate some of the input from user.
Once you get all the needed input, create the draft terraform code and show it to user for confirmation.
Interact with user to correct the draft terraform code if needed.
Then use the deploy function to deploy the terraform code.
"""

AVAILABLE_FUNCTIONS = {
            "get_sp": get_sp,
            "deploy": deploy,
            "validate": validate,

        } 

FUNCTIONS_SPEC= [  
    {
        "name": "get_sp",
        "description": "retrieve standard procedure to interact with user for a problem",
        "parameters": {
            "type": "object",
            "properties": {
            "user_request": { "type": "string", "description": "Detail description user request to generate terraform code" },


        },

    },
    },
    {
        "name": "validate",
        "description": "Validate SKU information ofthe terraform code",
        "parameters": {
            "type": "object",
            "properties": {
            "vm_sku": { "type": "string", "description": "name of the VM sku" },

        },

    },
    },

{
        "name": "deploy",
        "description": "Deploy terraform code",
        "parameters": {
            "type": "object",
            "properties": {
            "terraform_code": { "type": "string", "description": "Terraform code to deploy" },

        },

    },
    }

]  


def transcribe(audio_file):
    # transcript = openai.Audio.transcribe(os.getenv("WHISPER_DEPLOYMENT"), audio_file)
    # print(audio_file)
    headers={}
    headers['api-key']=os.getenv('WHISPER_AOAI_KEY')
    endpoint=os.getenv('WHISPER_AOAI_ENDPOINT')
    files = {
        'file': audio_file,
    }
    url=f"{endpoint}openai/deployments/{whisper_engine}/audio/transcriptions?api-version=2023-09-01-preview"
    response=requests.post(url,files=files,headers=headers,json={"language":"en"})
    return response


def save_audio_file(audio_bytes, file_extension):
    """
    Save audio bytes to a file with the specified extension.

    :param audio_bytes: Audio data in bytes
    :param file_extension: The extension of the output audio file
    :return: The name of the saved audio file
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"files/audio_{timestamp}.{file_extension}"

    with open(file_name, "wb") as f:
        f.write(audio_bytes)

    return file_name

@retry(stop=(stop_after_delay(1) | stop_after_attempt(5)))
def transcribe_audio(file_path):
    """
    Transcribe the audio file at the specified path.

    :param file_path: The path of the audio file to transcribe
    :return: The transcribed text
    """
    with open(file_path, "rb") as audio_file:
        transcript = transcribe(audio_file)
    return json.loads(transcript.text)['text']
