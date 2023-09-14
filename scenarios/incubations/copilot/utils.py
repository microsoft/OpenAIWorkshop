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
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
emb_engine = emb_engine.strip('"')
class Search_Client():
    def __init__(self,emb_map_file_path):
        with open(emb_map_file_path) as file:
            self.chunks_emb = json.load(file)

    def find_article(self,question, topk=3):  
        """  
        Given an input vector and a dictionary of label vectors,  
        returns the label with the highest cosine similarity to the input vector.  
        """  
        input_vector = get_embedding(question, engine = emb_engine)        
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
    index_name = index_name.strip('"')
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
    key = key.strip('"')
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    # Function to generate embeddings for title and content fields, also used for query embeddings
    def generate_embeddings(text):
        print("emb_engine", emb_engine)
        openai.api_version = "2023-05-15"
        response = openai.Embedding.create(
            input=text, engine=emb_engine)
        embeddings = response['data'][0]['embedding']
        return embeddings
    credential = AzureKeyCredential(key)
    azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)
else:
    faiss_search_client = Search_Client("../data/chunk_emb_map.json")

def search_knowledgebase_acs(search_query):
    vector = Vector(value=generate_embeddings(search_query), k=3, fields="embedding")
    print("search query: ", search_query)
    results = azcs_search_client.search(  
        search_text=search_query,  
        vectors= [vector],
        select=["sourcepage","content"],
        top=5
    )  
    text_content =""
    for result in results:  
        text_content += f"{result['sourcepage']}\n{result['content']}\n"
    print("text_content", text_content)
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

    def run(self, user_input, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        openai.api_version = api_version
        if user_input is None: #if no input return init message
            return self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        i=0
        query_used = None

        # while True:
        #     try:
        #         i+=1
        response = openai.ChatCompletion.create(
            deployment_id=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
            messages=conversation,
        functions=self.functions_spec,
        function_call="auto", 
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
                print("function list:", self.functions_list)
                raise Exception("Function " + function_name + " does not exist")
            function_to_call = self.functions_list[function_name]  
            
            # verify function has correct number of arguments
            function_args = json.loads(response_message["function_call"]["arguments"])

            if check_args(function_to_call, function_args) is False:
                raise Exception("Invalid number of arguments for function: " + function_name)
            

            # check if there's an opprotunity to use semantic cache
            if function_name =="search_knowledgebase":
                if os.getenv("USE_SEMANTIC_CACHE") == "True":
                    search_query = function_args["search_query"]
                    cache_output = get_cache(search_query)
                    if cache_output is not None:
                        print("semantic cache hit")
                        conversation.append({"role": "assistant", "content": cache_output})
                        return False, query_used,conversation, cache_output
                    else:
                        print("semantic cache missed")
                        query_used = search_query


            function_response = function_to_call(**function_args)
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

            return stream,query_used, conversation, assistant_response
        else:
            assistant_response = response_message["content"]
            conversation.append({"role": "assistant", "content": assistant_response})
            #     break
            # except Exception as e:
            #     if i>3: 
            #         assistant_response="Haizz, my memory is having some trouble, can you repeat what you just said?"
            #         break
            #     print("Exception as below, will retry\n", str(e))
            #     time.sleep(5)

        return False,query_used, conversation, assistant_response