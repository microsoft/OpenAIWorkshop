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
from azure.cosmos import CosmosClient
from datetime import datetime, timedelta
from dateutil import parser

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
cosmos_uri = os.environ.get("COSMOS_URI")
cosmos_key=os.environ.get("COSMOS_KEY")
container_name = os.getenv("COSMOS_CONTAINER_NAME")
cosmos_db_name = os.getenv("COSMOS_DB_NAME")
client = CosmosClient(cosmos_uri, credential=cosmos_key)
cosmos_db_client = client.get_database_client(cosmos_db_name)
cosmos_container_client = cosmos_db_client.get_container_client(container_name)

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
    def get_new_times(departure_time, delta):
        dp_dt = parser.parse(departure_time)
        
        new_dp_dt = dp_dt + timedelta(hours=delta)
        new_ar_dt = new_dp_dt + timedelta(hours=2)

        new_departure_time = new_dp_dt.strftime("%Y-%m-%dT%H:%M:%S")
        new_arrival_time = new_ar_dt.strftime("%Y-%m-%dT%H:%M:%S")
        return new_departure_time, new_arrival_time
    flights = ""
    for flight_num, delta in [("AA479", -1), ("AA490",-2), ("AA423",-3)]:
        new_departure_time, new_arrival_time = get_new_times(departure_time, delta)
        flights= flights +f"flight number {flight_num}, from: {from_}, to: {to}, departure_time: {new_departure_time}, arrival_time: {new_arrival_time}, flight_status: on time \n"
    return flights
def confirm_flight_change(current_ticket_number, new_flight_num, new_departure_time,new_arrival_time):
    # based on the input flight number and from, to and departure time, generate a random seat number and a random gate number and random amount of refund or extra charge for the flight change
    # then write a information message to the user with all the information 
    charge = 80
    #retrieve current flight

    old_flight={}
    for item in cosmos_container_client.query_items(
            query=f'SELECT * FROM c  WHERE c.ticket_num="{current_ticket_number}" AND c.status="open"',
            enable_cross_partition_query=True):
            
            old_flight['airline'] = item['airline']
            old_flight['customer_id'] = item['customer_id']
            old_flight['flight_num'] = item['flight_num']
            old_flight['seat_num'] = item['seat_num']
            old_flight['departure_airport'] = item['departure_airport']
            old_flight['seat_num'] = item['seat_num']
            old_flight['departure_airport'] = item['departure_airport']
            old_flight['arrival_airport'] = item['arrival_airport']
            old_flight['departure_time'] = item['departure_time']
            old_flight['arrival_time'] = item['arrival_time']
            old_flight['ticket_class'] = item['ticket_class']
            old_flight['ticket_num'] = item['ticket_num']
            old_flight['gate'] = item['gate']
            old_flight['id'] = item['id']
            old_flight['status'] = "cancelled"
            break
    #update the old flight status to cancelled
    cosmos_container_client.upsert_item(old_flight)
    print("updated old flight status to cancelled")
    #create a new flight
    #generate a new ticket number which is a 10 digit random number
    new_ticket_num = str(random.randint(1000000000, 9999999999))
    new_flight=old_flight.copy()
    new_flight["id"] = new_ticket_num
    new_flight['flight_num'] = new_flight_num
    new_flight['departure_time'] = new_departure_time
    new_flight['arrival_time'] = new_arrival_time
    new_flight['ticket_num'] = new_ticket_num
    new_flight['status'] = "open"
    cosmos_container_client.create_item(new_flight)
    
    return f"""Your new flight now is {new_flight_num} departing from {new_flight['departure_airport']} to {new_flight['arrival_airport']}. Your new departure time is {new_departure_time} and arrival time is {new_arrival_time}. Your new ticket number is {new_ticket_num}.
    Your credit card has been charged with an amount of ${charge} dollars for fare difference."""
def test_change_flight(current_ticket_number, current_flight_num, new_flight_num, from_):
    # based on the input flight number and from, to and departure time, generate a random seat number and a random gate number and random amount of refund or extra charge for the flight change
    # then write a information message to the user with all the information 
    charge = 80
    return f"Changing your ticket from {current_flight_num} to new flight {new_flight_num} departing from {from_} would cost {charge} dollars."

def load_user_flight_info(user_id):
    # Load flight information from CosmosDB
    matched_flights =[]
    for item in cosmos_container_client.query_items(
            query=f'SELECT * FROM c  WHERE c.customer_id="{user_id}" AND c.status="open"',
            enable_cross_partition_query=True):
            flight={}
            flight['airline'] = item['airline']
            flight['flight_num'] = item['flight_num']
            flight['seat_num'] = item['seat_num']
            flight['departure_airport'] = item['departure_airport']
            flight['seat_num'] = item['seat_num']
            flight['departure_airport'] = item['departure_airport']
            flight['arrival_airport'] = item['arrival_airport']
            flight['departure_time'] = item['departure_time']
            flight['arrival_time'] = item['arrival_time']
            flight['ticket_class'] = item['ticket_class']
            flight['ticket_num'] = item['ticket_num']
            flight['gate'] = item['gate']
            flight['status'] = item['status']
            matched_flights.append(flight)

    if len(matched_flights) == 0:
        return f"Sorry, we cannot find any flight information for you"

    return str(matched_flights)
PERSONA = """
You are Maya, an airline customer agent helping customers with questions and requests about their flight.
You are currently serving {customer_name} with id {customer_id}.
First, you need to look up their flight information and confirm with the customer about their flight information including flight number, from and to, departure and arrival time.
When you are asked with a general airline policy question such as baggage limit, use the search_knowledgebase function to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the information from the search. If asking a clarifying question to the user would help, ask the question.
When the user asks for a flight status, use check_flight_status function to check the flight status.
When the user asks to change their flight, first check the feasibility and cost of the change with check_change_flight function. If customer agrees with the change, execute the change with confirm_flight_change function.
If the user is asking for information that is not related to flight and airline, say it's not your area of expertise.
"""

AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "query_flights": query_flights,
            "confirm_flight_change": confirm_flight_change,
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
        "name": "confirm_flight_change",
        "description": "Execute the flight change after confirming with the customer",
        "parameters": {
            "type": "object",
            "properties": {
                    "current_ticket_number": {
                    "type": "string",
                    "description": "The current ticket number"
                },
                "new_flight_num": {
                    "type": "string",
                    "description": "The new flight number"
                },
                "new_departure_time": {
                    "type": "string",
                    "description": "The new departure time of the new flight"
                },
                "new_arrival_time": {
                    "type": "string",
                    "description": "The new arrival time of the new flight"
                },

            },
            "required": ["current_ticket_number", "new_flight_num", "new_departure_time", "new_arrival_time"],
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