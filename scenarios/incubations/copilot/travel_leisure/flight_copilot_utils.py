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
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)


env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")

client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version="2023-12-01-preview",
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
)

sqllite_db_path= os.environ.get("SQLITE_DB_PATH","data/flight_db.db")
engine = create_engine(f'sqlite:///{sqllite_db_path}') 
class Search_Client():
    def __init__(self,emb_map_file_path):
        with open(emb_map_file_path) as file:
            self.chunks_emb = json.load(file)

    def find_article(self,question, topk=3):  
        """  
        Given an input vector and a dictionary of label vectors,  
        returns the label with the highest cosine similarity to the input vector.  
        """  
        print("question ", question)
        input_vector = get_embedding(question, model = emb_engine)        
        # Compute cosine similarity between input vector and each label vector
        cosine_list=[]  
        for item in self.chunks_emb:  
            #by default, we use embedding for the entire content of the topic (plus topic descrition).
            # If you you want to use embedding on just topic name and description use this code cosine_sim = cosine_similarity(input_vector, vector[0])
            cosine_sim = 1 - spatial.distance.cosine(input_vector, item['policy_text_embedding'])
            cosine_list.append((item['id'],item['policy_text'],cosine_sim ))
        cosine_list.sort(key=lambda x:x[2],reverse=True)
        cosine_list= cosine_list[:topk]
        best_chunks =[chunk[0] for chunk in cosine_list]
        contents = [chunk[1] for chunk in cosine_list]
        text_content = ""
        for chunk_id, content in zip(best_chunks, contents):
            text_content += f"{chunk_id}\n{content}\n"

        return text_content
def check_args(function, args):
    sig = inspect.signature(function)
    params = sig.parameters

    # Check if there are extra arguments
    for name in args:
        if name not in params:
            return False
    # Check if the required arguments are provided 
    for name, param in params.items():
        if param.default is param.empty and name not in args:
            return False

def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

faiss_search_client = Search_Client("./data/flight_policy.json")

def search_airline_knowledgebase(search_query):
    print("search query: ", search_query)
    """  
    Given an input vector and a dictionary of label vectors,  
    returns the label with the highest cosine similarity to the input vector.  
    """  
    print("question ", search_query)
    return faiss_search_client.find_article(search_query, topk=3)

#uncomment to use Azure Cognitive Search

# service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
# index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
# key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
# credential = AzureKeyCredential(key)
# azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)
# SearchClient(service_endpoint, index_name =index_name , credential=credential)

# def search_airline_knowledgebase(search_query):

#     vector = VectorizedQuery(vector=get_embedding(search_query, model=emb_engine), k=3, fields="contentVector")
#     print("search query: ", search_query)
#     results = azcs_search_client.search(  
#         search_text=search_query,  
#         vector_queries= [vector],
#         # filter= product_filter,
#         select=["policy_type","policy"],
#         top=3
#     )  
#     text_content =""
#     for result in results:  
#         text_content += f"{result['policy_type']}\n{result['policy']}\n"
#     return text_content


def check_flight_status(flight_num, from_):
    # Query the SQLite database for the flight status
    result = session.query(Flight).filter_by(flight_num=flight_num, departure_airport=from_, status="open").first()

    if result is not None:
        # Assuming you want to return a string containing relevant flight information
        output = {
            'flight_num': result.flight_num,
            'departure_airport': result.departure_airport,
            'arrival_airport': result.arrival_airport,
            'departure_time': result.departure_time.strftime('%Y-%m-%d %H:%M'),
            'arrival_time': result.arrival_time.strftime('%Y-%m-%d %H:%M'),
            'status': result.status
        }
    else:
        output = f"Cannot find status for the flight {flight_num} from {from_}"

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
  
# Define the database model  
Base = declarative_base()  
  
class Customer(Base):
    __tablename__ = 'customers'
    id = Column(String, primary_key=True)
    name = Column(String)
    flights = relationship('Flight', backref='customer')

class Flight(Base):
    __tablename__ = 'flights'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey('customers.id'))
    ticket_num = Column(String)
    flight_num = Column(String)
    airline = Column(String)
    seat_num = Column(String)
    departure_airport = Column(String)
    arrival_airport = Column(String)
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    ticket_class = Column(String)
    gate = Column(String)
    status = Column(String)
  
# Set up the SQLite database  
Base.metadata.create_all(engine)  
Session = sessionmaker(bind=engine)  
session = Session()  
# Example usage  
# new_confirmation = confirm_flight_change("1234567890", "AA123", "2023-08-01 08:00", "2023-08-01 10:00")  
# print(new_confirmation)  

def confirm_flight_change(current_ticket_number, new_flight_num, new_departure_time, new_arrival_time):  
    charge = 80  
  
    # Retrieve current flight  
    old_flight = session.query(Flight).filter_by(ticket_num=current_ticket_number, status="open").first()  
    if old_flight:  
        old_flight.status = "cancelled"  
        session.commit()  
        print("Updated old flight status to cancelled")  
  
        # Create a new flight  
        new_ticket_num = str(random.randint(1000000000, 9999999999))  
        new_flight = Flight(  
            id=new_ticket_num,  
            ticket_num=new_ticket_num,  
            customer_id=old_flight.customer_id,  
            flight_num=new_flight_num,  
            seat_num=old_flight.seat_num,  # Assuming same seat for simplicity  
            airline=old_flight.airline,  # Assuming same airline for simplicity  
            departure_airport=old_flight.departure_airport,  
            arrival_airport=old_flight.arrival_airport,  
            departure_time=datetime.strptime(new_departure_time, '%Y-%m-%d %H:%M'),  
            arrival_time=datetime.strptime(new_arrival_time, '%Y-%m-%d %H:%M'),  
            ticket_class=old_flight.ticket_class,  
            gate=old_flight.gate,  # Assuming same gate for simplicity  
            status="open"  
        )  
        session.add(new_flight)  
        session.commit()  
          
        return f"""Your new flight now is {new_flight_num} departing from {new_flight.departure_airport} to {new_flight.arrival_airport}. Your new departure time is {new_departure_time} and arrival time is {new_arrival_time}. Your new ticket number is {new_ticket_num}.  
        Your credit card has been charged with an amount of ${charge} dollars for fare difference."""  
  
    else:  
        return "Could not find the current ticket to change."  
  

def check_change_booking(current_ticket_number, current_flight_num, new_flight_num, from_):
    # based on the input flight number and from, to and departure time, generate a random seat number and a random gate number and random amount of refund or extra charge for the flight change
    # then write a information message to the user with all the information 
    charge = 80
    return f"Changing your ticket from {current_flight_num} to new flight {new_flight_num} departing from {from_} would cost {charge} dollars."

def load_user_flight_info(user_id):
    # Load flight information from SQLite using SQLAlchemy
    user_id=user_id.strip()
    print("user_id", user_id)
    matched_flights = session.query(Flight).filter_by(customer_id=user_id, status="open").all()
    
    flights_info = []
    for flight in matched_flights:
        flight_info = {
            'airline': flight.airline,  # Assuming you have this field in the Flight model.
            'flight_num': flight.flight_num,
            'seat_num': flight.seat_num,
            'departure_airport': flight.departure_airport,
            'arrival_airport': flight.arrival_airport,
            'departure_time': flight.departure_time.strftime('%Y-%m-%d %H:%M'),
            'arrival_time': flight.arrival_time.strftime('%Y-%m-%d %H:%M'),
            'ticket_class': flight.ticket_class,
            'ticket_num': flight.ticket_num,
            'gate': flight.gate,
            'status': flight.status
        }
        flights_info.append(flight_info)

    if not flights_info:
        return "Sorry, we cannot find any flight information for you."

    return str(flights_info)

FLIGHT_PERSONA = """
You are Maya, an airline customer agent helping customers with questions and requests about their flight.
You are currently serving {customer_name} with id {customer_id}.
First, you need to look up their flight information and confirm with the customer about their flight information including flight number, from and to, departure and arrival time.
When you are asked with a general airline policy question such as baggage limit, use the search_airline_knowledgebase function to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the information from the search. If asking a clarifying question to the user would help, ask the question.
When the user asks for a flight status, use check_flight_status function to check the flight status.
When the user asks to change their flight, first check the feasibility and cost of the change with check_change_booking function. If customer agrees with the change, execute the change with confirm_flight_change function.
If user ask for anything that is not related with your responsibility, signal you get help first, don't just refuse to answer customer.
"""

FLIGHT_AVAILABLE_FUNCTIONS = {
            "search_airline_knowledgebase": search_airline_knowledgebase,
            "query_flights": query_flights,
            "confirm_flight_change": confirm_flight_change,
            "check_change_booking": check_change_booking,
            "check_flight_status": check_flight_status,
            "load_user_flight_info": load_user_flight_info

        } 

FLIGHT_FUNCTIONS_SPEC= [  
    {
        "type":"function",
        "function":{

        "name": "search_airline_knowledgebase",
        "description": "Searches the airline knowledge base to answer airline policy questions",
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
    
    }},
    {
        "type":"function",
        "function":{

        "name": "check_change_booking",
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

    }},

    {
        "type":"function",
        "function":{

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
                    "description": "The new departure time of the new flight in '%Y-%m-%d %H:%M' format"
                },
                "new_arrival_time": {
                    "type": "string",
                    "description": "The new arrival time of the new flight in '%Y-%m-%d %H:%M' format"
                },

            }},
            "required": ["current_ticket_number", "new_flight_num", "new_departure_time", "new_arrival_time"],
        },

    },
    {
        "type":"function",
        "function":{

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
    }},
    {
        "type":"function",
        "function":{
       
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
    }
]  




class Smart_Agent():
    """
    Agent that can use other agents and tools to answer questions.

    Args:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent. Defaults to None.
        engine (str): The name of the GPT engine to use. Defaults to "gpt-35-turbo".

    Methods:
        llm(new_input, stop, history=None, stream=False): Generates a response to the input using the LLM model.
        _run(new_input, stop, history=None, stream=False): Runs the agent and generates a response to the input.
        run(new_input, history=None, stream=False): Runs the agent and generates a response to the input.

    Attributes:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent.
        engine (str): The name of the GPT engine to use.
    """


    def __init__(self, persona,functions_spec, functions_list, name=None, init_message=None, engine =chat_engine):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.init_history =  init_hist
        self.persona = persona
        self.engine = engine
        self.name= name

        self.functions_spec = functions_spec
        self.functions_list= functions_list
        
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def run(self, user_input, conversation=None):
        if user_input is None: #if no input return init message
            return self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        request_help = False
        while True:
            response = client.chat.completions.create(
                model=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                messages=conversation,
            tools=self.functions_spec,
            tool_choice='auto',
            max_tokens=200,

            )
            
            response_message = response.choices[0].message
            if response_message.content is None:
                response_message.content = ""

            tool_calls = response_message.tool_calls
            

            print("assistant response: ", response_message.content)
            # Step 2: check if GPT wanted to call a function
            if  tool_calls:
                conversation.append(response_message)  # extend conversation with assistant's reply
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    print("Recommended Function call:")
                    print(function_name)
                    print()
                
                    # Step 3: call the function
                    # Note: the JSON response may not always be valid; be sure to handle errors
                                    
                    # verify function exists
                    if function_name not in self.functions_list:
                        # raise Exception("Function " + function_name + " does not exist")
                        conversation.pop()
                        continue
                    function_to_call = self.functions_list[function_name]
                    
                    # verify function has correct number of arguments
                    function_args = json.loads(tool_call.function.arguments)

                    if check_args(function_to_call, function_args) is False:
                        # raise Exception("Invalid number of arguments for function: " + function_name)
                        conversation.pop()
                        continue

                    
                    # print("beginning function call")
                    function_response = str(function_to_call(**function_args))

                    if function_name=="get_help": #scenario where the agent asks for help
                        summary_conversation = []
                        for message in conversation:
                            message = dict(message)
                            if message.get("role") != "system" and message.get("role") != "tool" and len(message.get("content"))>0:
                                summary_conversation.append({"role":message.get("role"), "content":message.get("content")})
                        summary_conversation.pop() #remove the last message which is the agent asking for help
                        return True, summary_conversation, function_response

                    print("Output of function call:")
                    print(function_response)
                    print()
                
                    conversation.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )  # extend conversation with function response
                    

                continue
            else:
                break #if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user

        conversation.append(response_message)
        assistant_response = response_message.content

        return request_help, conversation, assistant_response
