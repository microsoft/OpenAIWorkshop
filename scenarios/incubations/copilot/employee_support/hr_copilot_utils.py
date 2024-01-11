# Agent class
### responsbility definition: expertise, scope, conversation script, style 
from openai import AzureOpenAI

import os
from pathlib import Path  
import json
import time
from scipy import spatial  # for calculating vector similarities for search

from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
import inspect
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")

client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version="2023-12-01-preview",
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
)

import sys
import random
sys.path.append("..")
from utils import Agent, check_args


def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

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
        for chunk_id,chunk_content, vector in self.chunks_emb:  
            #by default, we use embedding for the entire content of the topic (plus topic descrition).
            # If you you want to use embedding on just topic name and description use this code cosine_sim = cosine_similarity(input_vector, vector[0])
            cosine_sim = 1 - spatial.distance.cosine(input_vector, vector)
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
    index_name = index_name.strip('"')
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
    key = key.strip('"')
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    # Function to generate embeddings for title and content fields, also used for query embeddings
    credential = AzureKeyCredential(key)
    azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)
else:
    faiss_search_client = Search_Client("../data/chunk_emb_map.json")



def search_knowledgebase_acs(search_query):

    vector = VectorizedQuery(vector=get_embedding(search_query, model=emb_engine), k=3, fields="embedding")
    print("search query: ", search_query)
    # print("products: ", products.split(","))
    # product_filter = " or ".join([f"product eq '{product}'" for product in products.split(",")])
    results = azcs_search_client.search(  
        search_text=search_query,  
        vector_queries= [vector],
        # filter= product_filter,
        query_type=QueryType.SEMANTIC, semantic_configuration_name='default', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
        select=["sourcepage","content"],
        top=3
    )  
    text_content =""
    for result in results:  
        text_content += f"{result['sourcepage']}\n{result['content']}\n"
    # print("text_content", text_content)
    return text_content

def search_knowledgebase(search_query):
    if os.getenv("USE_AZCS") == "True":
        print("using azcs")
        return search_knowledgebase_acs(search_query)
    else:
        print("using faiss")
        print(os.getenv("USE_AZCS"))
        return faiss_search_client.find_article(search_query)

###Sematic caching implementation
if os.getenv("USE_SEMANTIC_CACHE") == "True":
    cache_index_name = os.getenv("CACHE_INDEX_NAME")
    cache_index_name= cache_index_name.strip('"')
    azcs_semantic_cache_search_client = SearchClient(service_endpoint, cache_index_name, credential=credential)

def add_to_cache(search_query, gpt_response):
    search_doc = {
                 "id" : str(uuid.uuid4()),
                 "search_query" : search_query,
                 "search_query_vector" : get_embedding(search_query, engine=emb_engine),
                "gpt_response" : gpt_response
              }
    azcs_semantic_cache_search_client.upload_documents(documents = [search_doc])
def get_cache(search_query):
    vector = VectorizedQuery(vector=get_embedding(search_query, engine=emb_engine), k=3, fields="search_query_vector")
  
    results = azcs_semantic_cache_search_client.search(  
        search_text=None,  
        vector_queries= [vector],
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
        query_used = None
        while True:
            response = client.chat.completions.create(
                model=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                messages=conversation,
            tools=self.functions_spec,
            tool_choice='auto',
            
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
                        conversation.pop()
                        continue
                    
                    # print("beginning function call")
                    function_response = str(function_to_call(**function_args))
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

        return query_used, conversation, assistant_response

HR_PERSONA = """
You are Lucy, an HR support specialist responsible for answering questions about HR & Payroll from employees and handling personal information updates.
You start the conversation by validating the identity of the employee. Do not proceed until you have validated the identity of the employee.
When you are asked with a question, use the search tool to find relavent knowlege articles to create the answer. If the question is complex, be creative: do multiple searches and combine the answers.
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
        "type":"function",
        "function":{
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
    }
    },

    {
        "type":"function",
        "function":{

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
        }
    },
    {
        "type":"function",
        "function":{

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
        }
    },
    {
        "type":"function",
        "function":{
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

    }},

]  


