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

    def __init__(self, persona,functions_spec, functions_list, name=None, init_message=None, engine ="gpt-4"):
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

        while True:
            try:
                i+=1
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
                break
            except Exception as e:
                if i>3: 
                    assistant_response="Haizz, my memory is having some trouble, can you repeat what you just said?"
                    break
                print("Exception as below, will retry\n", str(e))
                time.sleep(8)

        return False,query_used, conversation, assistant_response