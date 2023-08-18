# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import time
import openai
import os
from pathlib import Path  
import json
import random
from dotenv import load_dotenv
from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
import ast
import pandas as pd
env_path = Path('..') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
import sys
sys.path.append("..")
from utils import Agent, Smart_Agent, check_args


def update_sales(filter, update):
    file_name = "../data/forecast_sales.json"
    filter = ast.literal_eval(filter)
    update = ast.literal_eval(update).items()
    update = list(update)[0]
    with open(file_name) as f:
        data = pd.read_json(f)
    filter_data = data.copy()
    for filter_item in filter.items():
        filter_data = filter_data[filter_data[filter_item[0]] == filter_item[1]]
    filter_data[update[0]]=update[1]
    print(filter_data)
    data.update(filter_data,overwrite=True)
    with open(file_name, 'w') as f:
        data.to_json(f)

    return f"Update sales forecast in with filter {filter} and update {update}"
def update_cost(filter, update):
    file_name = "../data/forecast_cost.json"
    filter = ast.literal_eval(filter)
    update = ast.literal_eval(update).items()
    update = list(update)[0]
    with open(file_name) as f:
        data = pd.read_json(f)
    filter_data = data.copy()
    for filter_item in filter.items():
        filter_data = filter_data[filter_data[filter_item[0]] == filter_item[1]]
    filter_data[update[0]]=update[1]
    print(filter_data)
    data.update(filter_data,overwrite=True)
    with open(file_name, 'w') as f:
        data.to_json(f)

    return f"Update cost forecast in with filter {filter} and update {update}"


def query_cost(filter):
    file_name = "../data/forecast_cost.json"
    filter = ast.literal_eval(filter)
    with open(file_name) as f:
        data = pd.read_json(f)
    for filter_item in filter.items():
        print(filter_item[0],filter_item[1])
        data = data[data[filter_item[0]] == filter_item[1]]

    return f"Query result: {data.to_dict(orient='records')}"
def query_sales(filter):
    file_name = "../data/forecast_sales.json"
    filter = ast.literal_eval(filter)
    with open(file_name) as f:
        data = pd.read_json(f)
    for filter_item in filter.items():
        print(filter_item[0],filter_item[1])
        data = data[data[filter_item[0]] == filter_item[1]]

    return f"Query result: {data.to_dict(orient='records')}"


def route_call(user_request):
    return f"The user request is {user_request}"

def validate_identity(employee_id, employee_name):
    if employee_id in ["1234","5678"]:
        return f"Employee {employee_name} with id {employee_id} is validated in this conversation"
    else:
        return "This employee id is not valid"
ROUTE_CALL_FUNCTION_NAME = "route_call" #default function name for routing call used by all agents
VALIDATE_IDENTIFY_FUNCTION_NAME = "validate_identity" #default function name for validating identity used by all agents
ROUTING_AGENT_PERSONA = """
You are Jenny, a helpful digital assistant helping to determine the right specialist to help users with needs.
Engage in the conversation with the user to understand the request and route the call to the right specialist.
Limit the conversation to understand what their request is about. 
There are 2 specialists available to help with the request:
    - Cost forecast data analyst responsible for helping users to query and update cost forecast information
    - Sales forecast data analyst responsible for helping users to query and update sales forecast information
If there's ambiguity in the request, ask for clarification till you know for sure which agent to route the call to.
Act as a single point of contact. Users don't need to know that there are 2 agents available to help with the request.
If none of the agent's profile match the request, apologize that the scope of service only cover the above 2 areas and end the conversation.
"""

SALES_FORECAST_PERSONA = """
You are Lucy, an information system specialist responsible for helping users maintaining sales forecast data.
You are given following data entity:
    {
        "name": "sales_forecast",
        "description": "contain data about sales forecast",
        "attributes": 
		{
            "name": "date",
            "description": "date of the sales data in dd/mm/yyyy, ranging from 01/01/2010 to 31/12/2024"
        },
		{
            "name": "business_unit",
            "description": "name of the business_unit, as one of the following values ['commercial', 'residential','government']
        },
		{
            "name": "amount",
            "description": "forecast sales amount",
        },
		{
            "name": "product",
            "description": "product that generates sales, as one of the following values ['heater', 'air conditioner' ,'fan']"
        },
    },
If the user request is to update the sales forecast, you need to:
- Interact with the user to confirm the changes that need to be made. Your goal is to identify the attribute values that help locate the data entity and the new 
attribute values that need to be updated.
- You need at least date, business_unit and product to locate the data entity.
- For attributes that have restriction in the value, for example business_unit, you need to validate the new value is in the list of allowed values.
- If there's ambiguity in user's request, you need to ask for clarification. 
- Once you can confirm all the information, summarize and confirm with user.
- If they agree, use the update tool to update the data entity.
If the user request is to query the sales forecast, you need to:
- Interact with the user to confirm the filter condition for the query. Your goal is to identify the attribute values that help locate the data entity.
- You need at least date, business_unit and product to locate the data entity.
- For attributes that have restriction in the value, for example business_unit, you need to validate the new value is in the list of allowed values.
- If there's ambiguity in user's request, you need to ask for clarification. 
- Use the information query tool to query the data.
- Only use data that is from the search tool to answer question. Do not generate answer that is not from the tool.
For any other request, call route_call function.
"""

COST_FORECAST_PERSONA = """
You are Betty, an information system specialist responsible for helping users maintaining cost forecast data.
You are given following data entity:
    {
        "name": "cost_forecast",
        "description": "contain data about cost forecast data",
        "attributes": 
		{
            "name": "date",
            "description": "date of the cost data in dd/mm/yyyy, ranging from 01/01/2010 to 31/12/2024"
        },
		{
            "name": "business_unit",
            "description": "name of the business_unit, as one of the following values ['commercial', 'residential','government']
        },
		{
            "name": "amount",
            "description": "actual amount",
        },
		{
            "name": "product",
            "description": "product that generates sales, as one of the following values ['heater', 'air conditioner' ,'fan']"
        },
    },
If the user request is to update the cost forecast, you need to:
- Interact with the user to confirm the changes that need to be made. Your goal is to identify the attribute values that help locate the data entity and the new 
attribute values that need to be updated.
- You need at least date, business_unit and product to locate the data entity.
- For attributes that have restriction in the value, for example business_unit, you need to validate the new value is in the list of allowed values.
- If there's ambiguity in user's request, you need to ask for clarification. 
- Once you can confirm all the information, summarize and confirm with user.
- If they agree, use the update tool to update the data entity.
If the user request is to query the cost forecast, you need to:
- Interact with the user to confirm the filter condition for the query. Your goal is to identify the attribute values that help locate the data entity.
- You need at least date, business_unit and product to locate the data entity.
- For attributes that have restriction in the value, for example business_unit, you need to validate the new value is in the list of allowed values.
- If there's ambiguity in user's request, you need to ask for clarification. 
- Use the information query tool to query the data.
- Only use data that is from the search tool to answer question. Do not generate answer that is not from the tool.
For any other request, call route_call function.
"""



COST_AVAILABLE_FUNCTIONS = {
            "update_cost": update_cost,
            "query_cost": query_cost,

            "route_call": route_call

        } 
SALES_AVAILABLE_FUNCTIONS = {
            "update_sales": update_sales,
            "query_sales": query_sales,
            "route_call": route_call

        } 


ROUTING_AGENT_FUNCTIONS = {
            "route_call": route_call,

        } 
ROUTING_AGENT_FUNCTIONS_SPEC= [  
    {
        "name": "route_call",
        "description": "Call this function to transfer the call to the right agent",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Description of what user wants to do"
                },

            },
            "required": ["user_request"],
        },
    }

]  


SALES_FORECAST_FUNCTIONS_SPEC= [  
    {
        "name": "update_sales",
        "description": "Update sales forecast data only, not other data entities",
        "parameters": {
            "type": "object",
            "properties": {

                "filter": {
                    "type": "string",
                    "description": "attribute name and value pairs to filter the data to update, for example {'date':'01/01/2021','business_unit':'commercial'}"
                },
                "update": {
                    "type": "string",
                    "description": "attribute name and value pairs to update the data entity, for example {'amount':'1000'}"
                }

            },
            "required": ["filter","update"],
        },

    },
    {
        "name": "query_sales",
        "description": "Query tool for sales forecast only, not other data entities",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "attribute name and value pairs to filter the data, for example {'date':'2021-01=01','business_unit':'commercial'}"
                }
            },
            "required": ["filter"],
        },

    },


    {
        "name": "route_call",
        "description": "Handle request that is not about querying or updating sales forecast data",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Description of what user wants to do"
                },

            },
            "required": ["user_request"],
        },

    },


]  
COST_FORECAST_FUNCTIONS_SPEC= [  
    {
        "name": "update_cost",
        "description": "Update cost forecast data only, not other data entities",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "attribute name and value pairs to filter the data to update, for example {'date':'01/01/2021','business_unit':'commercial'}"
                },
                "update": {
                    "type": "string",
                    "description": "attribute name and value pairs to update the data entity, for example {'amount':'1000'}"
                }

            },
            "required": ["filter","update"],
        },

    },
    {
        "name": "query_cost",
        "description": "Query tool for cost forecast only, not for sales forecast",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "attribute name and value pairs to filter the data, for example {'date':'2021-01=01','business_unit':'commercial'}"
                }
            },
            "required": ["filter"],
        },

    },


    {
        "name": "route_call",
        "description": "Handle  request that is not about querying or updating cost forecast data",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Description of what user wants to do"
                },

            },
            "required": ["user_request"],
        },

    },


]  


class Agent_Runner():
    def __init__(self,starting_agent_name, agents, session_state) -> None:
        self.agents = agents
        self.session_state = session_state
        self.active_agent = None
        for agent in agents:
            if starting_agent_name == agent.name:
                self.active_agent = agent
                break
        evaluator_persona ="Jenny: a general customer support agent, handling everyting except sales forecast or cost forecast\n\n Lucy: a specialist agent responsible for sales forecast\n\n Betty: a specialist agent responsible for cost forecast\n\n"        
        self.evaluator = Agent(engine="turbo-0613", persona="As a customer support manager, you need to assign call transfer requests to the right agent with the right skills. You have following agents with the description of their persona: \n\n"+evaluator_persona)
        
    def revaluate_agent_assignment(self,function_description):
        #TODO: revaluate agent assignment based on the state
        names = [agent.name for agent in self.agents]
        prompt =f"The most suitable agent's name among [{names}] to best match with this request [{function_description}] is "
        count =0
        while True:
            count+=1
            if count > 3:
                next_agent = random.choice(names)
                print("cannot decide on the agent, randomly assigned to ", next_agent)
                break
            next_agent = self.evaluator.generate_response(prompt).strip()
            if next_agent==self.active_agent.name: #should be different from the current agent
                continue
            if next_agent in names:
                break
        print("next agent ", next_agent)
        for agent in self.agents:
            if next_agent == agent.name:
                self.active_agent = agent
                print("agent changed to ", agent.name)
                break
    def run(self,user_input, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        stream_out, request_agent_change, context_to_persist, conversation, assistant_response= self.active_agent.run(user_input, conversation=conversation, stream = stream, api_version = api_version)
        if context_to_persist is not None:
            self.session_state['user_context'] = context_to_persist
        if request_agent_change:
            # previous_agent_last_response = assistant_response
            self.revaluate_agent_assignment(request_agent_change)
            new_conversation= self.active_agent.init_history
            #this code is to transfer any implicit context (context which is not in conversation like user's credentials) from the previous agent to the new agent to its system message
            if self.session_state['user_context'] is not None and len(self.session_state["user_context"])>0:
                old_system_message = new_conversation[0]
                new_system_message = old_system_message['content'] + "\n\n" + self.session_state['user_context']
                conversation[0] = {"role":"system", "content":new_system_message}
            
            #adding relevant content from the old agent to the new agent
            for message in conversation:
                if message.get("role") != "system" and message.get("name") is  None: #only add user & assistant messages
                    new_conversation.append({"role":message.get("role"), "content":message.get("content")})
            stream_out, _,_,conversation, assistant_response= self.active_agent.run(conversation=new_conversation, stream = False, api_version = api_version)
        return stream_out, request_agent_change, conversation, assistant_response


def stream_write(st, agent_response):
    message_placeholder = st.empty()
    full_response = ""
    for response in agent_response:
        if len(response.choices)>0:
            full_response += response.choices[0].delta.get("content", "")
            message_placeholder.markdown(full_response + "▌")
    message_placeholder.markdown(full_response)
    return full_response

class Smart_Coordinating_Agent(Smart_Agent):
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

    def run(self, user_input=None, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        openai.api_version = api_version
        request_agent_change = False
        context_to_persist = None
        assistant_response=""
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        if  user_input is not None:
            conversation.append({"role": "user", "content": user_input})
        i=0
        while True: # loop to retry in case there's an intermittent error from GPT

            try:
                i+=1
                response = openai.ChatCompletion.create(
                    deployment_id=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                    messages=conversation,
                functions=self.functions_spec,
                function_call="auto", 
                request_timeout=20,
                )
                response_message = response["choices"][0]["message"]

                # Step 2: check if GPT wanted to call a function
                if  response_message.get("function_call"):
                    print("Recommended Function call:")
                    print(response_message.get("function_call"))
                    print()
                    
                    # Step 3: call the function
                    # Note: the JSON response may not always be valid; be sure to handle errors
                    
                    function_name = response_message["function_call"]["name"]
                    if function_name == ROUTE_CALL_FUNCTION_NAME:
                        request_agent_change = True
                        
                        
                    # verify function exists
                    if function_name not in self.functions_list:
                        print("Function " + function_name + " does not exist")

                    function_to_call = self.functions_list[function_name]  
                    
                    # verify function has correct number of arguments
                    function_args = json.loads(response_message["function_call"]["arguments"])
                    if check_args(function_to_call, function_args) is False:
                        print("Invalid number of arguments for function: " + function_name)
                    function_response = function_to_call(**function_args)
                    print("Output of function call:")
                    print(function_response)
                    print()
                    if request_agent_change:
                        request_agent_change = function_response # if the function is a route call function, assign the request_agent_change to be the name of department to change to
                    
                    # adding assistant response to messages
                    conversation.append(
                        {
                            "role": response_message["role"],
                            "name": response_message["function_call"]["name"],
                            "content": response_message["function_call"]["arguments"],
                        }
                    )

                    # adding function response to messages
                    conversation.append(
                        {
                            "role": "function",
                            "name": function_name,
                            "content": function_response,
                        }
                    )  # extend conversation with function response
                    openai.api_version = api_version
                    second_response = openai.ChatCompletion.create(
                        messages=conversation,
                        deployment_id=self.engine,
                        stream=stream,
                    )  # get a new response from GPT where it can see the function response
                    
                    if not stream:
                        assistant_response = second_response["choices"][0]["message"]["content"]
                        conversation.append({"role": "assistant", "content": assistant_response})

                    else:
                        assistant_response = second_response

                    return stream,request_agent_change,context_to_persist,conversation, assistant_response

                else:
                    assistant_response = response_message["content"]
                    conversation.append({"role": "assistant", "content": assistant_response})
                break
            except Exception as e:
                if i>3: 
                    assistant_response="Haizz, my memory is having some trouble, can you repeat what you just said?"

                    break
                print("Exception as below, will retry\n", str(e))
                time.sleep(8)

        return False, request_agent_change,context_to_persist, conversation, assistant_response

