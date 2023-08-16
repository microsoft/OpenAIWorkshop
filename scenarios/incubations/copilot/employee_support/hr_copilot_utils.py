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
env_path = Path('..') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
import sys
import random
sys.path.append("..")
from utils import Agent, Smart_Agent, check_args, search_knowledgebase


    



HR_PERSONA = """
You are Lucy, an HR support specialist responsible for answering questions about HR & Payroll from employees and handling personal information updates.
You start the conversation by validating the identity of the employee. Do not proceed until you have validated the identity of the employee.
When you are asked with a question, use the search tool to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
When employee request updating their address, interact with them to get their new country, new state, new city and zipcode. If they don't provide new country, check if it's still United States. Make sure you have all information then use update address tool provided to update in the system. 
For all other information update requests, log a ticket to the HR team to update the information.
If the employee is asking for information that is not related to HR or Payroll, say it's not your area of expertise.
"""

def validate_identity(employee_id, employee_name):
    if employee_id in ["1234","5678"]:
        return f"Employee {employee_name} with id {employee_id} is validated in this conversation"
    else:
        return "This employee id is not valid"
def update_address(employee_id, country, state, city, zipcode):
    return f"Address of employee {employee_id} address has been updated to {country}, {state}, {city}, {zipcode}"
def create_ticket(employee_id, updates):
    return f"A ticket number 1233445 has been created for employee {employee_id} with the following updates: {updates} "

HR_AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "validate_identity": validate_identity,
            "update_address": update_address,
            "create_ticket": create_ticket,

        } 

HR_FUNCTIONS_SPEC= [  
    {
        "name": "search_knowledgebase",
        "description": "Searches the knowledge base for an answer to the HR/Payroll question",
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
    {
        "name": "validate_identity",
        "description": "validates the identity of the employee",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "The employee id to validate"
                },
                "employee_name": {
                    "type": "string",
                    "description": "The employee id to validate"
                }

            },
            "required": ["employee_id", "employee_name"],
        },

    },
    {
        "name": "update_address",
        "description": "Update the address of the employee",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "The employee id to validate"
                },
                "city": {
                    "type": "string",
                    "description": "The new city to update"
                },
                "state": {
                    "type": "string",
                    "description": "The new state to update"
                },
                "zipcode": {
                    "type": "integer",
                    "description": "The new zipcode to update"
                },
                "country": {
                    "type": "string",
                    "description": "The new country to update"
                }

            },
            "required": ["employee_id","city", "state", "zipcode", "country"],
        },

    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket for the employee to update personal information other than address",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "The employee id to validate"
                },
                "updates": {
                    "type": "string",
                    "description": "The new/changed information to update"
                }

            },
            "required": ["employee_id","updates"],
        },

    },

]  


