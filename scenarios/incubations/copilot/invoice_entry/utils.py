import openai
import dotenv
from pathlib import Path
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
whisper_engine = os.getenv("WHISPER_DEPLOYMENT")
@retry(stop=(stop_after_delay(1) | stop_after_attempt(5)))
def query_invoice(sql_query):
    # Read invoices from JSONL file
    invoices = []
    with open("data/invoices.jsonl", "r") as f:
        for line in f:
            invoice = json.loads(line)
            invoices.append(invoice)

    # Convert invoices to pandas DataFrame
    invoices = pd.json_normalize(invoices, record_path="line_items", meta=["invoice_number", "vendor_name", "vendor_address", "total_amount", "invoice_date", "due_date"])

    # Execute SQL query on DataFrame
    try:
        result = sqldf(sql_query, locals())
        return result.to_markdown()
    except:
        return "no data found" 

def resolve_vendor_name(vendor_name):
    # Load vendors from JSONL file
    with open("data/vendors.jsonl", "r") as f:
        vendors = [json.loads(line) for line in f]

    # Try to match vendor name exactly
    for vendor in vendors:
        if vendor_name.lower() == vendor["vendor_name"].lower():
            return f"Vendor name \"{vendor_name}\" is valid", False

    # Try to match vendor name partially using fuzzy matching
    for vendor in vendors:
        if fuzz.partial_ratio(vendor_name.lower(), vendor["vendor_name"].lower()) >= 80:
            return vendor["vendor_name"], True# fuzzy match

    # If no match is found, return "Not found"
    return f"Not found", False
    

def validate_invoice(**kwargs):
    #for simplicity, we only validate vendor name
    vendor_name = kwargs["vendor_name"]
    resolved_vendor_name, fuzzy_match = resolve_vendor_name(vendor_name)
    if fuzzy_match:
        return f"Vendor name \"{vendor_name}\" not found. Did you mean \"{resolved_vendor_name}\"?"
    elif resolved_vendor_name == "Not found":
        return f"Vendor name \"{vendor_name}\" not found."
    return "Entered information is valid"
def create_invoice(**kwargs):
    return f"Invoice {kwargs['invoice_number']} created successfully"
PERSONA = """
You are an accountant helping to create entry into the accounting system for a new invoice.
You interact with user to capture the following information into the accounting system.
Invoice header:
- Invoice number
- Invoice date
- Invoice amount
- Vendor name
- Vendor address
Invoice's line items
- Line item number
- Line item description
- Line item quantity
- Line item price
- Line item amount
When user provides information. even partial information, use the validate_invoice function to validate.
After you've captured all information, display the captured invoice using markdown table format for user to confirm.
Once the user confirms, use the create_invoice function to create the invoice in the accounting system.
User can also ask you to query the invoice in the accounting system. They can ask you to query by invoice number or by vendor name or by invoice date or by invoice amount. Use the query_invoice function to query the invoice in the accounting system.
"""

AVAILABLE_FUNCTIONS = {
            "create_invoice": create_invoice,
            "query_invoice": query_invoice,
            "validate_invoice": validate_invoice,

        } 

FUNCTIONS_SPEC= [  
    {
        "name": "create_invoice",
        "description": "Create an invoice in the accounting system",
        "parameters": {
            "type": "object",
            "properties": {
            "invoice_number": { "type": "string", "description": "The invoice number" },
            "invoice_date": { "type": "string", "description": "The invoice date" },
            "invoice_amount": { "type": "string", "description": "The invoice amount" },
            "vendor_name": { "type": "string", "description": "The vendor name" },
            "vendor_address": { "type": "string", "description": "The vendor address" },
            "invoice_line_items": { "type": "array", "description": "The invoice line items",
                    "items": {  
                        "line_item_number": { "type": "string", "description": "The line item number" },
                        "line_item_description": { "type": "string", "description": "The line item description" },
                        "line_item_amount": { "type": "string", "description": "The line item amount" },
                        "line_item_quantity": { "type": "string", "description": "The line item quantity" },
                        "line_item_price": { "type": "string", "description": "The line item price" },

                    },
            },


        },

    },
    },
    {
        "name": "validate_invoice",
        "description": "Validate information of an invoice",
        "parameters": {
            "type": "object",
            "properties": {
            "vendor_name": { "type": "string", "description": "The vendor name" },
            "invoice_line_items": { "type": "array", "description": "The invoice line items",
                    "items": {  
                        "line_item_description": { "type": "string", "description": "The line item description" },

                    },
            },


        },

    },
    },

{
        "name": "query_invoice",
        "description": "Query invoice in the accounting system",
        "parameters": {
            "type": "object",
            "properties": {
            "sql_query": { "type": "string", "description": "The SQL query to select the data from the invoices table. The columns in the invoices table are invoice_number, vendor_name, vendor_address, total_amount, invoice_date, due_date" },

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
transcript_text=None
with st.sidebar:
    st.title("Whisper Transcription")


    audio_bytes = audio_recorder("click to record", "stop")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        save_audio_file(audio_bytes, "mp3")
    
        # Find the newest audio file
        audio_file_path = max(
            ["files/"+f for f in os.listdir("./files") if f.startswith("audio")],
            key=os.path.getctime,
        )

        # Transcribe the audio file
        transcript_text = transcribe_audio(audio_file_path)