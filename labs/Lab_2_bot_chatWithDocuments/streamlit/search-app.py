import streamlit as st
import os
import sys
import requests
import json
import pandas as pd
sys.path.append('../')

from dotenv import load_dotenv
from pathlib import Path  # Python 3.6+ only


#env_path = os.path.join(".","scenarios","openai_on_custom_dataset","streamlit","secrets.env")
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

# Check if secrets.env exists and if not error out
if not os.path.exists(env_path):
    print("Missing secrets.env file with environment variables. Please create one and try again. See README.md for more details")
    exit(1)

# NOTE: You need to create a secret.env file to run this in the same folder with these variables

AZURE_ORCHESTRATOR_FUNC_APP_URL = os.environ.get("AZURE_ORCHESTRATOR_FUNC_APP_URL","MissingOrchestratorURL")

faq =["is AML SDK v2 compatible with v1?",
"Is GPU supported in AML?",
"What is hyper parameter tuning in AML?"
      ]


st.set_page_config(layout="wide")

col1, col2, col3  = st.columns((2,8, 2)) 
option = col2.selectbox('FAQs',faq)
question = col2.text_area("", option, height=100, placeholder="please enter your question" )

if col2.button("Submit"):  
    # call azure function app url
    if question:
        response = requests.post(AZURE_ORCHESTRATOR_FUNC_APP_URL, json={"prompt":question})
        if response.status_code == 200:
            response_json = response.json()
            col2.write(response_json["result"])
            col2.write(response_json["gpt_prompt"])
        else:
            col2.write("No results found")