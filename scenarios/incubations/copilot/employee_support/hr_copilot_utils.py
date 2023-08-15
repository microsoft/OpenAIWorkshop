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
from utils import Agent, Smart_Agent, check_args

class Search_Client():
    def __init__(self,emb_map_file_path):
        with open(emb_map_file_path) as file:
            self.chunks_emb = json.load(file)

    def find_article(self,question, topk=3):  
        """  
        Given an input vector and a dictionary of label vectors,  
        returns the label with the highest cosine similarity to the input vector.  
        """  
        input_vector = get_embedding(question, engine = 'text-embedding-ada-002')        
        # Compute cosine similarity between input vector and each label vector
        cosine_list=[]  
        for chunk_id,chunk_content, vector in self.chunks_emb:  
            #by default, we use embedding for the entire content of the topic (plus topic descrition).
            # If you you want to use embedding on just topic name and description use this code cosine_sim = cosine_similarity(input_vector, vector[0])
            cosine_sim = cosine_similarity(input_vector, vector) 
            cosine_list.append((chunk_id,chunk_content,cosine_sim ))
        cosine_list.sort(key=lambda x:x[2],reverse=True)
        cosine_list= cosine_list[:topk]
        best_chunks =[chunk[0] for chunk in cosine_list]
        contents = [chunk[1] for chunk in cosine_list]
        text_content = ""
        for chunk_id, content in zip(best_chunks, contents):
            text_content += f"{chunk_id}\n{content}\n"

        return text_content


#azcs implementation
if os.getenv("USE_AZCS") == "True":
    service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    # Function to generate embeddings for title and content fields, also used for query embeddings
    def generate_embeddings(text):
        response = openai.Embedding.create(
            input=text, engine="text-embedding-ada-002")
        embeddings = response['data'][0]['embedding']
        return embeddings

    credential = AzureKeyCredential(key)
    azcs_search_client = SearchClient(service_endpoint, index_name, credential=credential)
else:
    faiss_search_client = Search_Client("../data/chunk_emb_map.json")

def search_knowledgebase_acs(search_query):
    vector = Vector(value=generate_embeddings(search_query), k=3, fields="contentVector")
  
    results = azcs_search_client.search(  
        search_text=None,  
        vectors= [vector],
        select=["id", "content"],
    )  
    text_content =""
    for result in results:  
        text_content += f"{result['id']}\n{result['content']}\n"
    return text_content

def search_knowledgebase_faiss(search_query):
    return faiss_search_client.find_article(search_query)

def search_knowledgebase(search_query):
    if os.getenv("USE_AZCS") == "True":
        print("using azcs")
        return search_knowledgebase_acs(search_query)
    else:
        print("using faiss")
        return search_knowledgebase_faiss(search_query)



###Sematic caching implementation
if os.getenv("USE_SEMANTIC_CACHE") == "True":
    cache_index_name = os.getenv("CACHE_INDEX_NAME")
    azcs_semantic_cache_search_client = SearchClient(service_endpoint, cache_index_name, credential=credential)

def add_to_cache(search_query, gpt_response):
    search_doc = {
                 "id" : str(uuid.uuid4()),
                 "search_query" : search_query,
                 "search_query_vector" : generate_embeddings(search_query),
                "gpt_response" : gpt_response
              }
    azcs_semantic_cache_search_client.upload_documents(documents = [search_doc])

def get_cache(search_query):
    vector = Vector(value=generate_embeddings(search_query), k=3, fields="search_query_vector")
  
    results = azcs_semantic_cache_search_client.search(  
        search_text=None,  
        vectors= [vector],
        select=["gpt_response"],
    )  
    try:
        result =next(results)
        print("threshold ", result['@search.score'])
        if result['@search.score']>= float(os.getenv("SEMANTIC_HIT_THRESHOLD")):
            return result['gpt_response']
    except StopIteration:
        pass

    return None

    



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

def validate_identity(employee_id):
    if employee_id in ["1234","5678"]:
        return "valid employee"
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
                }
            },
            "required": ["employee_id"],
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


#function for multi-agents



 
def route_call(next_agent):
    return f"Request transfering to {next_agent}"

def validate_identity(employee_id, employee_name):
    if employee_id in ["1234","5678"]:
        return f"Employee {employee_name} with id {employee_id} is validated in this conversation"
    else:
        return "This employee id is not valid"
ROUTE_CALL_FUNCTION_NAME = "route_call" #default function name for routing call used by all agents
VALIDATE_IDENTIFY_FUNCTION_NAME = "validate_identity" #default function name for validating identity used by all agents
GENERALIST_PERSONA = """
You are Jenny, a helpful general assistant that can answer general questions about everything except HR and Payroll and IT.
You start the conversation by validating the identity of the employee. Do not proceed until you have validated the identity of the employee.
If the employee is asking for information in the HR & Payroll, inform that you will route the call to the right specialist.
If the employee is asking for information in the IT, inform that you will route the call to the right specialist.
"""
IT_PERSONA = """
You are Paul, a helpful IT specialist that help employees about everything in IT.
If the employee is asking for information that is not related to IT, inform employee that you will route the call to the right specialist.
"""

HR_PERSONA = """
You are Lucy, an HR support specialist responsible for answering questions about HR & Payroll from employees and handling personal information updates.
When you are asked with a question, always use the search tool to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
When employee request updating their address, use the tool provided to update in the system.
For all other information update requests, log a ticket to the HR team to update the information.
If the employee is asking for information that is not related to HR or Payroll, inform that you will route the call to the right specialist.
"""

HR_AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "update_address": update_address,
            "create_ticket": create_ticket,
            "route_call": route_call

        } 
IT_AVAILABLE_FUNCTIONS = {
            "route_call": route_call,

        } 

GENERAL_AVAILABLE_FUNCTIONS = {
            "route_call": route_call,
            "validate_identity": validate_identity,

        } 
GENERAL_FUNCTIONS_SPEC= [  
    {
        "name": "route_call",
        "description": "When the employee wants to talk about a topic that is not in your area of expertise, call this function to route request the transfer",
        "parameters": {
            "type": "object",
            "properties": {
                "next_agent": {
                    "type": "string",
                    "description": "description of the agent you think the call route the call should be routed to"
                },

            },
            "required": ["department"],
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


]  
IT_FUNCTIONS_SPEC= [  
    {
        "name": "route_call",
        "description": "When the employee wants to talk about a topic that is not in your area of expertise, call this function to route request the transfer",
        "parameters": {
            "type": "object",
            "properties": {
                "next_agent": {
                    "type": "string",
                    "description": "description of the agent you think the call route the call should be routed to"
                },

            },
            "required": ["department"],
        },

    },

]  



class Agent_Runner():
    def __init__(self,starting_agent_name, agents, session_state) -> None:
        self.agents = agents
        self.session_state = session_state
        self.active_agent = None
        for agent in agents:
            print("agent name",agent.name, "starting agent name", starting_agent_name)
            if starting_agent_name == agent.name:
                self.active_agent = agent
                break
        agent_descriptions ="Jenny: a general customer support agent, handling everyting except HR, Payroll and IT\n\n Lucy: a specialist support agent in HR and Payroll\n\n Paul: a specialist support agent in IT\n\n"        
        self.evaluator = Agent(engine="turbo-0613", persona="As a customer support manager, you need to assign call transfer requests to the right agent with the right skills. You have following agents with the description of their persona: \n\n"+agent_descriptions)
        
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
        previous_agent_last_response=None
        if context_to_persist is not None:
            self.session_state['user_context'] = context_to_persist
        if request_agent_change:
            previous_agent_last_response = assistant_response
            self.revaluate_agent_assignment(request_agent_change)
            conversation= self.active_agent.init_history
            #this code is to transfer the context (in this case user's credentials) from the previous agent to the new agent
            if self.session_state['user_context'] is not None:
                old_system_message = conversation[0]
                new_system_message = old_system_message['content'] + "\n\n" + self.session_state['user_context']
                conversation[0] = {"role":"system", "content":new_system_message}
            conversation.append({"role":"user", "content":user_input})
            stream_out, _,_,conversation, assistant_response= self.active_agent.run(conversation=conversation, stream = False, api_version = api_version)
        return stream_out, previous_agent_last_response, conversation, assistant_response


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
                    if function_name==VALIDATE_IDENTIFY_FUNCTION_NAME:
                        context_to_persist = function_response
                    # Step 4: send the info on the function call and function response to GPT
                    
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


