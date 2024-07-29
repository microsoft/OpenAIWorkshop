# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import sys  
from io import StringIO  
import contextlib  
from pathlib import Path  
import json
import os 
import base64
import traceback
from openai import AzureOpenAI
from sqlalchemy import create_engine  
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
import matplotlib.pyplot as plt
import streamlit as st
from plotly.io import write_image
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
import time
import requests
from azure.search.documents.models import (

    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)


import shutil
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  
import pandas as pd
from dotenv import load_dotenv
import inspect
import openai
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
MAX_ERROR_RUN = 3
MAX_RUN_PER_QUESTION =10
MAX_QUESTION_TO_KEEP = 3
MAX_QUESTION_WITH_DETAIL_HIST = 1

emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT"),
)
max_conversation_len = 5  # Set the desired value of k


emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
#azcs implementation
searchservice = os.getenv("AZURE_SEARCH_ENDPOINT") 
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
key = os.getenv("AZURE_SEARCH_KEY") 
search_client = SearchClient(  
        endpoint=searchservice,  
        index_name=index_name,  
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))  
    )  



# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

credential = AzureKeyCredential(key)
def get_text_embedding(text, model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")):  
    text = text.replace("\n", " ")  
    while True:  
        try:  
            embedding_response = client.embeddings.create(input = [text], model=model).data[0].embedding
            return embedding_response  
        except openai.error.RateLimitError:  
            print("Rate limit exceeded. Retrying after 10 seconds...")  
            time.sleep(10)  


today = pd.Timestamp.today()
#format today's date
today = today.strftime("%Y-%m-%d")
PERSONA = """
You are an intelligent AI assistant designed to help users find information most relevant to their questions. 
You have access to Azure AI Search, which provides semantic search capabilities using natural language queries and return a list of images with description.
Review the results, pick ONLY those that matches user's request and respond.
Your final response should be in JSON format like this:
{
  "overall_explanation": "Your overall explanation to the question",
  "videos/car_street1/scene_2_frame_1256_3.jpg": "description of the image how it matches the question",
  "videos/chrome_ads/scene_20_frame_674_3.jpg": "description of the image how it matches the question."
}
Just output the JSON content in your final response and do not add any other comment.


"""
def get_text_embedding_mm(text):
    key = os.getenv("AZURE_AI_VISION_API_KEY")

    # Vectorize Image API
    endpoint = os.getenv("AZURE_AI_VISION_ENDPOINT") + "computervision/"
    version = "?api-version=2024-02-01&model-version=2023-04-15"
    vectorize_img_url = endpoint + "retrieval:vectorizeText" + version
    data = json.dumps({"text":text})
    headers = {
        "Content-type": "application/json",
        "Ocp-Apim-Subscription-Key": key
    }

    try:
        r = requests.post(vectorize_img_url, data=data, headers=headers)

        if r.status_code == 200:
            image_vector = r.json()["vector"]
            return image_vector
        else:
            print(f"An error occurred while processing {text}. Error code: {r.status_code}.")

    except Exception as e:
        print(f"An error occurred while processing {text}: {e}")

    return None


def search(search_query):
    print("search query: ", search_query)
    vector_query = VectorizedQuery(vector=get_text_embedding(search_query), k_nearest_neighbors=3, fields="contentVector")
    image_query = VectorizedQuery(vector=get_text_embedding_mm(search_query), k_nearest_neighbors=3, fields="imageVector")

    results = search_client.search(  
        search_text=search_query,  

        query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
    
        vector_queries= [vector_query,image_query],
        select=[ "file_name", "description", "frame_filename", "frame_time"],
        top=3
    )  
    images_directory="./videos" 
    output = []
    for result in results:  
        page_image = os.path.join(images_directory,result['file_name'].split(".")[0], result['frame_filename'])
        output.append({'image_path':page_image, 'description':result['description'], "image_time": result['frame_time'] })
    return output
    

AVAILABLE_FUNCTIONS = {
            "search": search,
        } 


FUNCTIONS_SPEC= [  
    
    {
        "type":"function",
        "function":{

        "name": "search",
        "description": "Semantic Search Engine to search for content",

        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Natural language query to search for content" 
                }


            },
            "required": ["search_query"],
        },
    }
    },


]  



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
def clean_up_history(history, max_q_with_detail_hist=1, max_q_to_keep=2):
    # start from end of history, count the messages with role user, if the count is more than max_q_with_detail_hist, remove messages from there with roles tool.
    # if the count is more than max_q_hist_to_keep, remove all messages from there until message number 1
    question_count=0
    removal_indices=[]
    for idx in range(len(history)-1, 0, -1):
        message = dict(history[idx])
        if message.get("role") == "user":
            question_count +=1
            # print("question_count added, it becomes: ", question_count)   
        if question_count>= max_q_with_detail_hist and question_count < max_q_to_keep:
            if message.get("role") != "user" and message.get("role") != "assistant" and len(message.get("content")) == 0:
                removal_indices.append(idx)
        if question_count >= max_q_to_keep:
            removal_indices.append(idx)
    
    # remove items with indices in removal_indices
    for index in removal_indices:
        del history[index]

def reset_history_to_last_question(history):
    #pop messages from history from last item to the message with role user
    for i in range(len(history)-1, -1, -1):
        message = dict(history[i])   
        if message.get("role") == "user":
            break
        history.pop()

class Smart_Agent():
    """
    """

    def __init__(self, persona,functions_spec, functions_list, name=None, init_message=None, engine =chat_engine):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.conversation =  init_hist
        self.persona = persona
        self.engine = engine
        self.name= name

        self.functions_spec = functions_spec
        self.functions_list= functions_list
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def run(self, user_input, conversation=None, stream = False, ):
        if user_input is None: #if no input return init message
            return self.conversation, self.conversation[1]["content"]
        if conversation is not None: #if no history return init message
            self.conversation = conversation
        
        self.conversation.append({"role": "user", "content": user_input, "name": "James"})
        clean_up_history(self.conversation, max_q_with_detail_hist=MAX_QUESTION_WITH_DETAIL_HIST, max_q_to_keep=MAX_QUESTION_TO_KEEP)
            
        execution_error_count=0
        code = ""
        response_message = None
        data ={}
        execution_context={}
        run_count =0
        while True:
            if run_count >= MAX_RUN_PER_QUESTION:
                reset_history_to_last_question(self.conversation)
                print(f"Need to move on from this question due to max run count reached ({run_count} runs)")
                response_message= {"role": "assistant", "content": "I am unable to answer this question at the moment, please ask another question."}
                break
            if execution_error_count >= MAX_ERROR_RUN:
                reset_history_to_last_question(self.conversation)
                print(f"resetting history due to too many errors ({execution_error_count} errors) in the code execution")
                execution_error_count=0
            response = client.chat.completions.create(
                model=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                messages=self.conversation,
                tools=self.functions_spec,

            tool_choice='auto',
              temperature=0.2,

            
            )
            run_count+=1
            response_message = response.choices[0].message
            if response_message.content is None:
                response_message.content = ""
            tool_calls = response_message.tool_calls
            

            if  tool_calls:
                # print("Tool calls: ")
                self.conversation.append(response_message)  # extend conversation with assistant's reply
                for tool_call in tool_calls:
                    function_name = tool_call.function.name

                    print("Recommended Function call:")
                    print(function_name)
                    print()

                    # verify function exists
                    if function_name not in self.functions_list:
                        # raise Exception("Function " + function_name + " does not exist")
                        print(("Function " + function_name + " does not exist, retrying"))
                        self.conversation.pop()
                        break
                    function_to_call = self.functions_list[function_name]
                    
                    # verify function has correct number of arguments
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(e)
                        self.conversation.pop()
                        break
                    if check_args(function_to_call, function_args) is False:
                        self.conversation.pop()
                        break


                    else:
                        function_response = function_to_call(**function_args)
                                     
                    if function_name == "search":
                            search_function_response = []
                            for item in function_response:
                                image_path = item['image_path']
                                description =item['description']

                                with open(image_path, "rb") as image_file:
                                    base64_image= base64.b64encode(image_file.read()).decode('utf-8')
                                # path= "_".join(image_path.split("\\")[-2:])
                                print("image_path: ", image_path)

                                search_function_response.append({"type":"text", "text":f"file_name: {image_path}"})
                                search_function_response.append({"type": "image_url","image_url": {"url":  f"data:image/jpeg;base64,{base64_image}"}})
                                search_function_response.append({"type":"text", "text":f"this is the description of the image: {description}"})

                            function_response=search_function_response            
                    self.conversation.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )  # extend conversation with function response
                    

                continue
            else:
                # print('no function call')
                break #if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user

        if not stream:
            self.conversation.append(response_message)
            if type(response_message) is dict:
                assistant_response = response_message.get('content')
            else:
                assistant_response = response_message.dict().get('content')
            # conversation.append({"role": "assistant", "content": assistant_response})

        else:
            assistant_response = response_message

        return stream,code, self.conversation, assistant_response, data