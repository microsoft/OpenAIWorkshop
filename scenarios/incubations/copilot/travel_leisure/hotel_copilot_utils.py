# Agent class
### responsbility definition: expertise, scope, conversation script, style 
from openai import AzureOpenAI
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import sessionmaker  
from datetime import datetime  
import os
from pathlib import Path  
import json
import time
from scipy import spatial  # for calculating vector similarities for search
from datetime import datetime, timedelta
from dateutil import parser

from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)
import random
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  
import pandas as pd
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
import inspect
from azure.search.documents import SearchClient  
from dotenv import load_dotenv
from flight_copilot_utils import Smart_Agent, Search_Client
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
# azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)

# This function should remain unchanged as it is context-neutral
faiss_search_client = Search_Client("./data/hotel_policy.json")

def search_hotel_knowledgebase(search_query):
    print("search query: ", search_query)
    """  
    Given an input vector and a dictionary of label vectors,  
    returns the label with the highest cosine similarity to the input vector.  
    """  
    print("question ", search_query)
    return faiss_search_client.find_article(search_query, topk=3)

from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Customer(Base):  
    __tablename__ = 'customers'  
    id = Column(String, primary_key=True)  
    name = Column(String)  
    reservations = relationship('Reservation', backref='customer')  
  
class Reservation(Base):  
    __tablename__ = 'reservations'  
    id = Column(Integer, primary_key=True, autoincrement=True)  
    customer_id = Column(String, ForeignKey('customers.id'))  
    hotel_id = Column(String)  
    room_type = Column(String)  
    check_in_date = Column(DateTime)  
    check_out_date = Column(DateTime)  
    status = Column(String)  # e.g., "booked", "cancelled", "checked_in", "checked_out"  
    # Add any other relevant fields that describe the room or the reservation
engine = create_engine('sqlite:///data/hotel.db')

Base.metadata.create_all(engine)  
Session = sessionmaker(bind=engine)  
session = Session()  
def get_help(user_request):
    return f"{user_request}"


# This function should query the database for the reservation status instead of flight status
def check_reservation_status(reservation_id):
    # Query the SQLite database for the reservation status
    result = session.query(Reservation).filter_by(id=reservation_id, status="booked").first()

    if result is not None:
        # Assuming you want to return a string containing relevant reservation information
        output = {
            'reservation_id': result.id,
            'customer_id': result.customer_id,
            'room_type': result.room_type,
            'hotel_id': result.hotel_id,
            'check_in_date': result.check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': result.check_out_date.strftime('%Y-%m-%d'),
            'status': result.status
        }
    else:
        output = f"Cannot find status for the reservation with ID {reservation_id}"

    return str(output)

# This function should query available rooms instead of flights
def query_rooms(hotel_id, check_in_date, check_out_date):
    # For simplicity, generate 3 room types with random availability and return the list of rooms to the user
    room_types = ["Standard", "Deluxe", "Suite"]
    rooms = ""
    for room_type in room_types:
        # Here we would normally check the database for availability, but we'll assume all are available for the example
        rooms += f"Room type: {room_type}, Hotel ID: {hotel_id}, Check-in: {check_in_date}, Check-out: {check_out_date}, Status: Available\n"
    return rooms

# This function should change a hotel reservation instead of a flight
def confirm_reservation_change(current_reservation_id, new_room_type, new_check_in_date, new_check_out_date):
    charge = 50  # Assume a fixed change fee
  
    # Retrieve current reservation
    old_reservation = session.query(Reservation).filter_by(id=current_reservation_id, status="booked").first()  
    if old_reservation:  
        old_reservation.status = "cancelled"  
        session.commit()  
  
        # Create a new reservation
        new_reservation_id = str(random.randint(100000, 999999))  
        new_reservation = Reservation(  
            id=new_reservation_id,  
            customer_id=old_reservation.customer_id,  
            hotel_id=old_reservation.hotel_id,  
            room_type= new_room_type,
            check_in_date=datetime.strptime(new_check_in_date, '%Y-%m-%d'),  
            check_out_date=datetime.strptime(new_check_out_date, '%Y-%m-%d'),  
            status="booked"  
        )  
        session.add(new_reservation)  
        session.commit()  
  
        return f"Your new reservation for a {new_room_type} room is confirmed. Check-in date is {new_check_in_date} and check-out date is {new_check_out_date}. Your new reservation ID is {new_reservation_id}. A charge of ${charge} has been applied for the change."
  
    else:  
        return "Could not find the current reservation to change."

# This function should check the feasibility and outcome of a reservation change
def check_change_reservation(current_reservation_id, new_check_in_date, new_check_out_date, new_room_type):
    # For simplicity, assume the change is always possible and return a fixed charge
    charge = 50
    return f"Changing your reservation will cost an additional ${charge}."

# This function should load user reservation information instead of flight information
def load_user_reservation_info(user_id):
    user_id = user_id.strip()
    matched_reservations = session.query(Reservation).filter_by(customer_id=user_id, status="booked").all()
    
    reservations_info = []
    for reservation in matched_reservations:
        reservation_info = {
            'room_type': reservation.room_type,
            'hotel_id': reservation.hotel_id,
            'check_in_date': reservation.check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': reservation.check_out_date.strftime('%Y-%m-%d'),
            'reservation_id': reservation.id,
            'status': reservation.status
        }
        reservations_info.append(reservation_info)

    if not reservations_info:
        return "Sorry, we cannot find any reservation information for you."

    return str(reservations_info)

# Note: The above functions assume that you have a database with tables


HOTEL_PERSONA = """
You are Anna, a hotel customer service agent helping customers with questions and requests about their hotel reservations.
You are currently serving {customer_name} with id {customer_id}.
First, you need to look up their reservation information and confirm with the customer about their booking details including room type, check-in and check-out dates, and any special requests.
When you are asked with a general hotel policy question such as check-in time or pet policy, use the search_hotel_knowledgebase function to find relevant knowledge articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the information from the search. If asking a clarifying question to the user would help, ask the question.
When the user asks for a reservation status, use check_reservation_status function to check the booking details.
When the user asks to change their reservation, first check the feasibility and cost of the change with check_change_reservation function. If customer agrees with the change, execute the change with confirm_reservation_change function.
If user ask for anything that is not related with your responsibility, signal you get help first, don't just refuse to answer customer.

"""

HOTEL_AVAILABLE_FUNCTIONS = {
            "search_hotel_knowledgebase": search_hotel_knowledgebase,
            "query_rooms": query_rooms,
            "confirm_reservation_change": confirm_reservation_change,
            "check_change_reservation": check_change_reservation,
            "check_reservation_status": check_reservation_status,
            "load_user_reservation_info": load_user_reservation_info,
            "get_help": get_help
        }

HOTEL_FUNCTIONS_SPEC = [  
    # The search_hotel_knowledgebase function remains unchanged
    # The load_user_reservation_info function remains unchanged
    # The get_help function remains unchanged

    # The query_rooms function replaces the query_flights function
    {
        "type":"function",
        "function":{

        "name": "search_hotel_knowledgebase",
        "description": "Searches the hotel knowledge base to answer hotel policy questions",
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

    }},

    {
        "type":"function",
        "function":{
       
        "name": "load_user_reservation_info",
        "description": "Loads the hotel reservation for a user",
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
    },
    {
        "type":"function",
        "function":{
            "name": "query_rooms",
            "description": "Query the list of available rooms for a given hotel, check-in date, and check-out date",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotel_id": {
                        "type": "string",
                        "description": "The hotel id"
                    },
                    "check_in_date": {
                        "type": "string",
                        "description": "The check-in date"
                    },
                    "check_out_date": {
                        "type": "string",
                        "description": "The check-out date"
                    }
                },
                "required": ["hotel_id", "check_in_date", "check_out_date"],
            },
        }
    },
    # The check_change_reservation function replaces the check_change_flight function
    {
        "type":"function",
        "function":{
            "name": "check_change_reservation",
            "description": "Check the feasibility and outcome of a presumed reservation change by providing current reservation details and new reservation details",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_reservation_id": {
                        "type": "string",
                        "description": "The current reservation id"
                    },
                    "new_check_in_date": {
                        "type": "string",
                        "description": "The new check-in date"
                    },
                    "new_check_out_date": {
                        "type": "string",
                        "description": "The new check-out date"
                    },
                    "new_room_type": {
                        "type": "string",
                        "description": "The new room type"
                    }
                },
                "required": ["current_reservation_id", "new_check_in_date", "new_check_out_date", "new_room_type"],
            },
        }
    },
    # The confirm_reservation_change function replaces the confirm_flight_change function
    {
        "type":"function",
        "function":{
            "name": "confirm_reservation_change",
            "description": "Execute the reservation change after confirming with the customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_reservation_id": {
                        "type": "string",
                        "description": "The current reservation id"
                    },
                    "new_room_type": {
                        "type": "string",
                        "description": "The new room type"
                    },
                    "new_check_in_date": {
                        "type": "string",
                        "description": "The new check-in date"
                    },
                    "new_check_out_date": {
                        "type": "string",
                        "description": "The new check-out date"
                    }
                },
                "required": ["current_reservation_id", "new_room_type", "new_check_in_date", "new_check_out_date"],
            },
        }
    },
    # The check_reservation_status function replaces the check_flight_status function
    {
        "type":"function",
        "function":{
            "name": "check_reservation_status",
            "description": "Checks the reservation status for a booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "string",
                        "description": "The reservation id"
                    }
                },
                "required": ["reservation_id"],
            },
        }
    }
]

