# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import openai
import os
from pathlib import Path  
import json
import time
from azure.search.documents.models import Vector  
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
# env_path = Path('.') / 'secrets.env'
# load_dotenv(dotenv_path=env_path)
# openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
# openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
# openai.api_type = "azure"
import sys
import random
from utils import Agent, Smart_Agent, check_args, search_knowledgebase
# service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
# index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
# index_name = index_name.strip('"')
# key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
# key = key.strip('"')
# emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
# credential = AzureKeyCredential(key)
# azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)


# def generate_embeddings(text):
#     openai.api_version = "2023-05-15"
#     response = openai.Embedding.create(
#         input=text, engine=emb_engine)
#     embeddings = response['data'][0]['embedding']
#     return embeddings
# def search_knowledgebase_acs(search_query):
#     vector = Vector(value=generate_embeddings(search_query), k=3, fields="embedding")
#     print("search query: ", search_query)
#     results = azcs_search_client.search(  
#         search_text=search_query,  
#         vectors= [vector],
#         select=["sourcepage","content"],
#         top=5
#     )  
#     text_content =""
#     for result in results:  
#         text_content += f"{result['sourcepage']}\n{result['content']}\n"
#     print("text_content", text_content)
#     return text_content




PERSONA = """
You are Maya, a technical support specialist responsible for answering questions about computer networking and system.
When you are asked with a question, use the search tool to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
If the user is asking for information that is not related to computer networking, say it's not your area of expertise.
"""

AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,

        } 

FUNCTIONS_SPEC= [  
    {
        "name": "search_knowledgebase",
        "description": "Searches the knowledge base for an answer to the technical question",
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "The search query to use to search the knowledge base"
                }
            },
            "required": ["search_query"],
        },
    },

]  


