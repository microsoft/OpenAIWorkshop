# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import openai
import os
from pathlib import Path  
import json
import re
from dotenv import load_dotenv
import concurrent.futures
from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"

class Search_Client():
    def __init__(self,emb_map_file_path):
        with open(emb_map_file_path) as file:
            self.chunks_emb = json.load(file)

    def find_article(self,question, topk=3):  
        openai.api_version = "2022-12-01"
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
def gpt_stream_wrapper(response):
    for chunk in response:
        chunk_msg= chunk['choices'][0]['delta']
        chunk_msg= chunk_msg.get('content',"")
        yield chunk_msg
class Agent(): #Base class for Agent
    def __init__(self, engine, persona, init_message=None):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.init_history =  init_hist
        self.persona = persona
        self.engine = engine
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



search_client = Search_Client("data/chunk_emb_map.json")

def search_knowlebase(search_query):
    return search_client.find_article(search_query)
def validate_identity(employee_id):
    if employee_id in ["1234","5678"]:
        return "valid employee"
    else:
        return "This employee id is not valid"
def update_address(employee_id, new_address):
    return f"Address of employee {employee_id} address has been updated to {new_address}"
def create_ticket(employee_id, updates):
    return f"A ticket number 1233445 has been created for employee {employee_id} with the following updates: {updates} "



available_functions = {
            "search_knowlebase": search_knowlebase,
            "validate_identity": validate_identity,
            "update_address": update_address,
            "create_ticket": create_ticket,

        } 

functions= [  
    {
        "name": "search_knowlebase",
        "description": "Searches the knowledge base for an answer to the question",
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
                "new_address": {
                    "type": "string",
                    "description": "The new address to update"
                }

            },
            "required": ["employee_id","new_address"],
        },

    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket for the employee to update other personal information",
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

    def __init__(self, persona,functions=functions, init_message=None, engine ="gpt-4"):
        super().__init__(engine, persona, init_message)
        #list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        self.tools = functions
    def run(self, user_input, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        openai.api_version = api_version
        if user_input is None: #if no input return init message
            return self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        response = openai.ChatCompletion.create(
            deployment_id=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
            messages=conversation,
        functions=self.tools,
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
            if function_name not in available_functions:
                return "Function " + function_name + " does not exist"
            function_to_call = available_functions[function_name]  
            
            # verify function has correct number of arguments
            function_args = json.loads(response_message["function_call"]["arguments"])
            if check_args(function_to_call, function_args) is False:
                return "Invalid number of arguments for function: " + function_name
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
                deployment_id=self.engine
            )  # get a new response from GPT where it can see the function response

            assistant_response = second_response['choices'][0]['message']["content"]
            conversation.append({"role": "assistant", "content": assistant_response})
        else:
            assistant_response = response_message["content"]
            conversation.append({"role": "assistant", "content": assistant_response})
        return conversation, assistant_response

