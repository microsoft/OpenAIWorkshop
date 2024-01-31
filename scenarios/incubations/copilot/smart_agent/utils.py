# Agent class
### responsbility definition: expertise, scope, conversation script, style 
from openai import AzureOpenAI
from datetime import datetime  
import os
from pathlib import Path  
import json
import time
from scipy import spatial  # for calculating vector similarities for search
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
import inspect

from azure.search.documents.models import (

    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)

env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")

client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version="2023-12-01-preview",
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
)
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
emb_engine = emb_engine.strip('"')

#azcs implementation
service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
index_name = index_name.strip('"')

key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
key = key.strip('"')

# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

credential = AzureKeyCredential(key)
azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)


def search_knowledgebase(search_query):

    vector = VectorizedQuery(vector=get_embedding(search_query), k_nearest_neighbors=3, fields="embedding")
    print("search query: ", search_query)
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


###Sematic caching implementation
if os.getenv("USE_SEMANTIC_CACHE") == "True":
    cache_index_name = os.getenv("CACHE_INDEX_NAME")
    cache_index_name= cache_index_name.strip('"')
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


def gpt_stream_wrapper(response):
    for chunk in response:
        chunk_msg= chunk['choices'][0]['delta']
        chunk_msg= chunk_msg.get('content',"")
        yield chunk_msg

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
                
PERSONA = """
You are Maya, a technical support specialist.
You are helping {username} with a technical question.
You will use the search tool to find relavent knowlege articles to create the answer.
Being smart in your research. If the search does not come back with the answer, rephrase the question and try again.
Review the result of the search and use it to guide your next search if needed.
If the question is complex, break down to smaller search steps and find the answer in multiple steps.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
If the user is asking for information that is not related to technical domain, say it's not your area of expertise.
"""

AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,

        } 

FUNCTIONS_SPEC= [  
    {
                                "type":"function",
        "function":{

        "name": "search_knowledgebase",
        "description": "Searches the knowledge base for an answer to the technical question",
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "The search query to use to search the knowledge base"
                },

            },
            "required": ["search_query"],
        },
    }},

]  


