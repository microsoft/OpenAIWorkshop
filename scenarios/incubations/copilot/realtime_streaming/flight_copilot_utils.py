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
import random
import sys
import random
sys.path.append("..")
from utils import Agent, Smart_Agent, check_args, search_knowledgebase

service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
index_name = index_name.strip('"')
key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
key = key.strip('"')


credential = AzureKeyCredential(key)
azcs_search_client = SearchClient(service_endpoint, index_name ="flights" , credential=credential)


def check_flight_status(flight_num, from_):
    filter=f"flight_num eq '{flight_num}'"

    results = azcs_search_client.search(  
        search_text=None,
        filter=filter,
        top=1

    )
    output =f"cannot find status for the flight {flight_num} "
    for result in results:
        output = result
    return str(output)

def query_flights(from_, to, departure_time):
    # generate 3 flights with random flight number in the format of AA1234 with different departure time and return the list of flights to the user
    #first convert the departure time to a datetime object assuming the format of the departutre time is '2020-09-20T10:30:00'  
    departure_time= '2020-09-20T10:30:00'
    arrival_time = '2020-12-20T10:30:00'
    #format both departure time and arrival time to string like '2020-09-20T10:30:00'
    flights = ""
    for i in range(3):
        flight_num = f"AA{random.randint(1000, 9999)}"
        flights= flights +f"flight_num {flight_num}, from: {from_}, to: {to}, departure_time: {departure_time}, arrival_time: {arrival_time}, flight_status: on time \n"
    return flights
def confirm_change_flight(current_ticket_number, current_flight_num, new_flight_num, from_):
    # based on the input flight number and from, to and departure time, generate a random seat number and a random gate number and random amount of refund or extra charge for the flight change
    # then write a information message to the user with all the information 
    charge = 80
    return f"Your new flight now is {new_flight_num} departing from {from_}. Your credit card has been charged with an amount of ${charge} dollars for fare difference."
def test_change_flight(current_ticket_number, current_flight_num, new_flight_num, from_):
    # based on the input flight number and from, to and departure time, generate a random seat number and a random gate number and random amount of refund or extra charge for the flight change
    # then write a information message to the user with all the information 
    charge = 80
    return f"Changing your ticket from {current_flight_num} to new flight {new_flight_num} departing from {from_} would cost {charge} dollars."

def load_user_flight_info(user_id):
    # load the json dictionary from the user profile file at data/user_profile.json. Then return the flight information for the user
    with open('./data/user_profile.json') as f:
        user_profile = json.load(f)
    return str(user_profile)
PERSONA = """
You are Maya, an airline customer agent helping customers with questions and requests about their flight.
You are currently serving {customer_name} with id {customer_id}.
First, you need to look up their flight information and confirm with the customer about their flight information including flight number, from and to, departure and arrival time.
When you are asked with a question knowlege question such as about their baggage limit, use the search tool to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the information from the search. If asking a clarifying question to the user would help, ask the question.
If the user is asking for information that is not related to flight and airline, say it's not your area of expertise.
When the user is asking for a flight status, you can use the flight status API to check the flight status.
When the user is asking to change their flight, first check the feasibility and consequence of the flight change, then if feasiable present information for confirmation from the customer. When customer agrees, execute the change.
"""

AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "query_flights": query_flights,
            "confirm_change_flight": confirm_change_flight,
            "check_change_flight": test_change_flight,
            "check_flight_status": check_flight_status,
            "load_user_flight_info": load_user_flight_info

        } 

FUNCTIONS_SPEC= [  
    {
        "name": "search_knowledgebase",
        "description": "Searches the knowledge base for an answer to the question",
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
        "name": "query_flights",
        "description": "Query the list of available flights for a given departure airport code, arrival airport code and departure time",
        "parameters": {
            "type": "object",
            "properties": {
                "from_": {
                    "type": "string",
                    "description": "The departure airport code"
                },
                "to": {
                    "type": "string",
                    "description": "The arrival airport code"
                },
                "departure_time": {
                    "type": "string",
                    "description": "The departure time"
                }
            },
            "required": ["from_", "to", "departure_time"],
        },
    
    },
    {
        "name": "check_change_flight",
        "description": "Check the feasibility and outcome of a presumed flight change by providing current flight information and new flight information",
        "parameters": {
            "type": "object",
            "properties": {
                    "current_ticket_number": {
                    "type": "string",
                    "description": "The current ticket number"
                },
                "current_flight_num": {
                    "type": "string",
                    "description": "The current flight number"
                },
                "new_flight_num": {
                    "type": "string",
                    "description": "The new flight number"
                },
                "from_": {
                    "type": "string",
                    "description": "The departure airport code"
                },
            },
            "required": ["current_ticket_number", "current_flight_num", "new_flight_num", "from_"],
        },

    },

    {
        "name": "confirm_change_flight",
        "description": "Execute change the flight for a customer",
        "parameters": {
            "type": "object",
            "properties": {
                    "current_ticket_number": {
                    "type": "string",
                    "description": "The current ticket number"
                },
                "current_flight_num": {
                    "type": "string",
                    "description": "The current flight number"
                },
                "new_flight_num": {
                    "type": "string",
                    "description": "The new flight number"
                },
                "from_": {
                    "type": "string",
                    "description": "The departure airport code"
                },
            },
            "required": ["current_ticket_number", "current_flight_num", "new_flight_num", "from_"],
        },

    },
    {
        "name": "check_flight_status",
        "description": "Checks the flight status for a flight",
        "parameters": {
            "type": "object",
            "properties": {

                "flight_num": {
                    "type": "string",
                    "description": "The flight number"
                },
                "from_": {
                    "type": "string",
                    "description": "The departure airport code"
                }
            },
            "required": ["flight_num", "from_"],
        },
    },
    {
        "name": "load_user_flight_info",
        "description": "Loads the flight information for a user",
        "parameters": {
            "type": "object",

            "properties": {
                "user_id": {

                    "type": "string",
                    "description": "The user id"
                }
            },
            "required": ["user_id"],
        },
    }

]  