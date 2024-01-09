# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import openai
import os
from pathlib import Path  
import json
import os 
from pprint import pprint
import requests
import base64

# from azure.search.documents.models import Vector  
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  
from langchain.utilities import BingSearchAPIWrapper

from dotenv import load_dotenv
# from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
print(os.environ.get("AZURE_OPENAI_API_KEY"))
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
import sys

class Agent(): #Base class for Agent
    def __init__(self, engine,persona, name=None, init_message=None):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.init_history =  init_hist
        self.persona = persona
        self.engine = engine
        self.name= name
    def generate_response(self, new_input,history=None, stream = False,request_timeout =20,api_version = "2023-05-15"):
        openai.api_version = api_version
        if new_input is None: # return init message 
            return self.init_history[1]["content"]
        messages = self.init_history.copy()
        if history is not None:
            for user_question, bot_response in history:
                messages.append({"role":"user", "content":user_question})
                messages.append({"role":"assistant", "content":bot_response})
        messages.append({"role":"user", "content":new_input})
        response = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            stream=stream,
            request_timeout =request_timeout
        )
        if not stream:
            return response['choices'][0]['message']['content']
        else:
            return gpt_stream_wrapper(response)
    def run(self, **kwargs):
        return self.generate_response(**kwargs)



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

    return True






PERSONA = """
You are Confluent Cloud AI assistant, helping users to execute tasks in Confluent Cloud platform.
Your responsibility includes: 1.Answer general knowledge questions about Confluent Cloud platform 2. Query customer's confluent cloud environment to answer questions specific to their environment
1. To answer general knowledge questions, you can use the search tool to find relavent knowlege articles to create the answer. Try to be smart in your research. If the search does not come back with the answer, rephrase the query and try again. If needed, perform the research in multiple steps in which you review the result of intermedidate search step and use it to guide your next search.
2. To query customer's confluent cloud environment, use GraphQL on Confluent Cloud's schema. To do this, follow the steps below:
    - Discover available graphql types in the customer's environment with the get_available_graphql_types function
    - Identify the graphql types that are relevant to the customer's question
    - Use the get_schema function to get the schema of the relevant graphql types identified above
    - Formulate a graphql query and use the execute_graphql function to query the customer's environment
    - Use the execute_graphql's result to formulate the response to the customer's question
    
If the user is asking for information that is not related to Confluent Cloud, say it's not your area of expertise.
"""
def search_knowledgebase(search_query, k=5):
    """
    Searches the knowledge base for an answer to the question.

    Args:
        search_query (str): The search query to use to search the knowledge base.

    Returns:
        str: The answer to the question.
    """

    # Add your Bing Search V7 subscription key and endpoint to your environment variables.
    search = BingSearchAPIWrapper(k=k)

    #limit to docs.confluent.io
    search_query = search_query +" site:docs.confluent.io"

    return search.run(search_query)

def execute_graphql(graphql_query):
    """
    Execute a graphql query on customer's environment

    Args:
        graphql_query (str): syntactically valid graphql query to retrieve information from customer's environment

    Returns:
        str: The result of the graphql query.
    """

    api_key = os.getenv("CF_API_KEY")
    api_secret = os.getenv("CF_API_SECRET")
    graphql_endpoint = os.getenv("CF_GRAPHQL_ENDPOINT")

    # Concatenate the API key and secret and encode them in Base64
    credentials = f"{api_key}:{api_secret}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    # Set up the headers with the encoded credentials
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_credentials}'
    }

    # Perform the HTTP POST request
    response = requests.post(graphql_endpoint, headers=headers, json={'query': graphql_query})

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        result = response.json()
        return result
    else:
        return f"Request failed with status code {response.status_code}: {response.text}"
def get_available_graphql_types():
    """
    Retrieve available graphql types in customer's environment

    Returns:
        str: The available graphql types in customer's environment.
    """

    graph_query = """
{
  __schema {
    types {
      name
      kind
    }
  }
}
"""
    return execute_graphql(graph_query)
def get_schema(graphql_type):
    """
    Retrieve detail schema of a graphql type

    Args:
        graphql_type (str): name of the graphql type to retrieve schema

    Returns:
        str: The schema of the graphql type.
    """

    graph_query = f"""
{{
  __type(name: "{graphql_type}") {{
    name
    kind
    description
    fields {{
      name
      description
      type {{
        name
        kind
      }}
    }}
  }}
}}
"""
    return execute_graphql(graph_query)


AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "get_schema": get_schema,
            "execute_graphql": execute_graphql,
            "get_available_graphql_types": get_available_graphql_types,

        } 

FUNCTIONS_SPEC= [  
    {
        "name": "search_knowledgebase",
        "description": "Searches the knowledge base",
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
        "name": "get_schema",
        "description": "Retrieve detail schema of a graphql type",
        "parameters": {
            "type": "object",
            "properties": {
                "graphql_type": {
                    "type": "string",
                    "description": "name of the graphql type to retrieve schema"
                }

            },
            "required": ["graphql_type"],
        },

    },
    {
        "name": "get_available_graphql_types",
        "description": "Retrieve available graphql types in customer's environment",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        },
    },
    {
        "name": "execute_graphql",
        "description": "execute a graphql query on customer's environment",
        "parameters": {
            "type": "object",
            "properties": {
                "graphql_query": {
                    "type": "string",
                    "description": "syntactically valid graphql query that relies on the schema of the discovered type(s). To filter result, only use following criteria expressions in the where clause: _eq (equal criteria), _lte (Less than or equals criteria), _gte (Greater or equals criteria), _gt (Greater than criteria), _lt (Less than criteria) and _starts_with (Starts with criteria). Also use _and, _or as logical operators. For example: {\\n  kafka_topic(where: {createTime: {_gte: \\\"2023-11-11T00:00:00Z\\\"}}) {\\n    name\\n    id\\n    createTime\\n  }\\n}\"}"
                }

            },
            "required": ["graphql_query"],
        },

    }

]  

def add_to_cache(search_query, gpt_response):
    search_doc = {
                 "id" : str(uuid.uuid4()),
                 "search_query" : search_query,
                 "search_query_vector" : get_embedding(search_query, engine=emb_engine),
                "gpt_response" : gpt_response
              }
    azcs_semantic_cache_search_client.upload_documents(documents = [search_doc])
def get_cache(search_query):
    vector = Vector(value=get_embedding(search_query, engine=emb_engine), k=3, fields="search_query_vector")
  
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

class Smart_Agent(Agent):
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

    def __init__(self, persona,functions_spec, functions_list, name=None, init_message=None, engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")):
        super().__init__(engine=engine,persona=persona, init_message=init_message, name=name)
        self.functions_spec = functions_spec
        self.functions_list= functions_list
        
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def run(self, user_input, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        # openai.api_version = api_version
        if user_input is None: #if no input return init message
            return self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        i=0
        query_used = None

        while True:

            response = openai.ChatCompletion.create(
                deployment_id=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                messages=conversation,
            functions=self.functions_spec,
            function_call="auto"
            
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
                
                # verify function exists
                if function_name not in self.functions_list:
                    raise Exception("Function " + function_name + " does not exist")
                function_to_call = self.functions_list[function_name]  
                
                # verify function has correct number of arguments
                function_args = json.loads(response_message["function_call"]["arguments"])

                if check_args(function_to_call, function_args) is False:
                    raise Exception("Invalid number of arguments for function: " + function_name)

                # check if there's an opprotunity to use semantic cache
                if function_name =="search_knowledgebase":
                    search_query = function_args["search_query"]
                    print("search_query", search_query)
                    if os.getenv("USE_SEMANTIC_CACHE") == "True":
                        
                        cache_output = get_cache(search_query)
                        if cache_output is not None:
                            print("semantic cache hit")
                            conversation.append({"role": "assistant", "content": cache_output})
                            return False, query_used,conversation, cache_output
                        else:
                            print("semantic cache missed")
                            query_used = search_query


                function_response = str(function_to_call(**function_args))
                print("Output of function call:")
                print(function_response)
                print()

                
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
                continue
            else:
                break #if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user

        if not stream:
            assistant_response = response_message["content"]
            conversation.append({"role": "assistant", "content": assistant_response})

        else:
            assistant_response = response_message
        return stream,query_used, conversation, assistant_response
