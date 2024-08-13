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
from dotenv import load_dotenv

env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)

evaluator_engine =  os.environ.get("AZURE_OPENAI_EVALUATOR_DEPLOYMENT")

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
from flight_copilot_utils import Smart_Agent, client,FLIGHT_PERSONA, FLIGHT_AVAILABLE_FUNCTIONS, FLIGHT_FUNCTIONS_SPEC 
from hotel_copilot_utils import  HOTEL_PERSONA, HOTEL_AVAILABLE_FUNCTIONS, HOTEL_FUNCTIONS_SPEC
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)


# Note: The above functions assume that you have a database with tables
def get_help(user_request):
    return f"{user_request}"


GENERALIST_PERSONA = """
You are Jenny, a helpful general assistant. Your job is to identify user's intent and forward the question to the right agent.
You are currently serving {customer_name} with id {customer_id}.
Once you are certain about what the customer is looking for, use get_help function to ask the right agent to chime in.
If user just ask generic questions not related to hotel or flight booking, feel free to help. No need to call other agents.
"""

FLIGHT_PERSONA = FLIGHT_PERSONA + "\nIf the user is asking for information that is not related to flight booking, just call for help and do not try to respond customer as it's violation of business policy."
HOTEL_PERSONA = HOTEL_PERSONA + "\nIf the user is asking for information that you cannot provide, just call for help so that other agents may help and do not try to respond customer as it's violation of business policy."
HOTEL_AVAILABLE_FUNCTIONS['get_help'] = get_help
FLIGHT_AVAILABLE_FUNCTIONS['get_help'] = get_help
get_help_function_spec ={        
    "type":"function",
        "function":{

        "name": "get_help",
        "description": "Transfer the conversation to an expert who can help the customer",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "summary user's request"
                },

            },
            "required": ["user_request"],
        },
    }
}

GENERALIST_FUNCTION_SPEC = [get_help_function_spec]
GENERALIST_AVAILABLE_FUNCTIONS = {'get_help':get_help}
HOTEL_FUNCTIONS_SPEC.append(get_help_function_spec)
FLIGHT_FUNCTIONS_SPEC.append(get_help_function_spec)
def classify_intent(user_input, candidates):
    agent_descriptions ="Jenny: a general customer support agent, handling general questions\n\n Maya: a specialist support agent in Flight booking\n\n Anna: a specialist support agent in Hotel booking\n\n"       
    prompt =f"Given the request [{user_input}], pick a name from [{candidates}]. Just output the name of the agent, no need to add any other text."
    messages = [{"role":"system", "content":"You are helpful AI assistant to match request with agent. Here are agents with the description of their responsibilties: \n\n"+agent_descriptions}, {"role":"user", "content":prompt}]
    response = client.chat.completions.create(
        model=evaluator_engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
        messages=messages,
        max_tokens=20,
    )
    response_message = response.choices[0].message.content
    print("classified as: ", response_message)

    return response_message.strip()

    
class Agent_Runner():
    def __init__(self,starting_agent_name, agents, session_state) -> None:
        self.agents = agents
        self.session_state = session_state
        self.active_agent = None
        for agent in agents:
            if starting_agent_name == agent.name:
                self.active_agent = agent
                break
    def revaluate_agent_assignment(self,function_description):
        #TODO: revaluate agent assignment based on the state
        candidates = [agent.name for agent in self.agents]
        count =0
        while True:
            count+=1
            if count > 3:
                next_agent = random.choice(candidates)
                print("cannot decide on the agent, randomly assigned to ", next_agent)
                break
            next_agent = classify_intent(function_description, candidates)
            if next_agent==self.active_agent.name: #should be different from the current agent
                continue
            if next_agent in candidates:
                break
        for agent in self.agents:
            if next_agent == agent.name:
                self.active_agent = agent
                print("agent changed to ", agent.name)
                break
    def run(self,user_input, conversation=None):
        get_help, conversation, assistant_response = self.active_agent.run(user_input=user_input, conversation=conversation)
        
        if get_help: #Agent signal to ask for help. Conversation history is reduced
            print("get help!")
            self.revaluate_agent_assignment(assistant_response)
            conversation=  conversation+self.active_agent.init_history
            
            get_help, conversation, assistant_response = self.active_agent.run(user_input=user_input, conversation=conversation)
        return  get_help, conversation, assistant_response


