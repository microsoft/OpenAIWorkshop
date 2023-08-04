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
env_path = Path('..') / 'secrets.env'
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

search_client = Search_Client("../data/chunk_emb_map.json")
 
def route_call(department):
    return f"conversation is routed to {department}"

def search_knowledgebase(search_query):
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

ROUTE_CALL_FUNCTION_NAME = "route_call" #default function name for routing call used by all agents
GENERALIST_PERSONA = """
You are Jenny, a helpful general assistant that can answer general questions about everything except HR and Payroll and IT.
If the employee is asking for information in the HR & Payroll, offer to route the call to HR/Payroll specialist then transfer the call.
If the employee is asking for information in the IT, offer to route the call to IT specialist then transfer the call.
"""
IT_PERSONA = """
You are Paul, a helpful IT specialist that help employees about everything in IT.
If the employee is asking for information that is not related to IT, offer to route the call to general customer support then transfer the call.
"""

HR_PERSONA = """
You are Lucy, an HR support specialist responsible for answering questions about HR & Payroll from employees and handling personal information updates.
You start the conversation by validating the identity of the employee. Do not proceed until you have validated the identity of the employee.
When you are asked with a question, use the search tool to find relavent knowlege articles to create the answer.
Answer ONLY with the facts from the search tool. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
When employee request updating their address, use the tool provided to update in the system.
For all other information update requests, log a ticket to the HR team to update the information.
If the employee is asking for information that is not related to HR or Payroll, offer to route the call to general customer support then transfer the call.
"""

HR_AVAILABLE_FUNCTIONS = {
            "search_knowledgebase": search_knowledgebase,
            "validate_identity": validate_identity,
            "update_address": update_address,
            "create_ticket": create_ticket,
            "route_call": route_call

        } 
IT_AVAILABLE_FUNCTIONS = {
            "route_call": route_call

        } 

GENERAL_AVAILABLE_FUNCTIONS = {
            "route_call": route_call

        } 
GENERAL_FUNCTIONS_SPEC= [  
    {
        "name": "route_call",
        "description": "When the employee wants to talk about a topic that is not in IT, call this function to route the call to the appropriate department",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "department to route the call to"
                },

            },
            "required": ["department"],
        },

    },


]  
IT_FUNCTIONS_SPEC= [  
    {
        "name": "route_call",
        "description": "When the employee wants to talk about a topic that is not in IT, call this function to route the call to the appropriate department",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "department to route the call to"
                },

            },
            "required": ["department"],
        },

    },


]  


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
    {
        "name": "route_call",
        "description": "When the employee wants to talk about a topic that is not in IT, call this function to route the call to the appropriate department",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "department to route the call to"
                },

            },
            "required": ["department"],
        },

    },


]  


class Agent_Runner():
    def __init__(self,starting_agent_name, agents) -> None:
        self.agents = agents

        self.active_agent = None
        for agent in agents:
            if starting_agent_name == agent.name:
                self.active_agent = agent
                break
        agent_descriptions = [(agent.name, agent.persona)for agent in self.agents]
        text_description =""
        for agent, description in agent_descriptions:
            text_description += f"Name: {agent}, Job description: {description}\n\n"
        
        self.evaluator = Agent(engine="turbo-0613", persona="As a customer support manager, you have following agents with the description of their skills\n\n"+text_description)
        
    def revaluate_agent_assignment(self,conversation_history):
        #TODO: revaluate agent assignment based on the state
        names = [agent.name for agent in self.agents]
        prompt =f"Review the last part of this conversation where there's a need to change the agent handling the call \n\{conversation_history[-4:]})\n\n. The most appropriate agent's name among {names} to take over the conversation is: "
        next_agent = self.evaluator.generate_response(prompt).strip()
        print("next agent ", next_agent)
        for agent in self.agents:
            if next_agent == agent.name:
                self.active_agent = agent
                print("agent changed to ", agent.name)
                break
            else:
                print("agent not changed to ", agent.name)
    def run(self,user_input, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        request_agent_change, conversation, assistant_response= self.active_agent.run(user_input, conversation=conversation, stream = False, api_version = api_version)
        previous_agent_last_response=None
        
        if request_agent_change:
            previous_agent_last_response = assistant_response
            self.revaluate_agent_assignment(conversation)
            conversation= self.active_agent.init_history
            conversation.append({"role":"user", "content":user_input})
            # conversation.append({"role":"assistant", "content":f"Agent {self.active_agent.name} is taking over the conversation."})
            _,conversation, assistant_response= self.active_agent.run(conversation=conversation, stream = False, api_version = api_version)
        return previous_agent_last_response, conversation, assistant_response
        

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
        super().__init__(engine=engine,persona=persona, name=name, init_message=init_message)
        self.functions_spec = functions_spec
        self.functions_list= functions_list
    def run(self, user_input=None, conversation=None, stream = False, api_version = "2023-07-01-preview"):
        openai.api_version = api_version
        request_agent_change = False
        # if user_input is None: #if no input return init message
        #     return self.init_history, self.init_history[1]["content"]
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
                stream=stream,
                request_timeout=15,
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

                    assistant_response = second_response['choices'][0]['message']["content"]
                    conversation.append({"role": "assistant", "content": assistant_response})

                else:
                    assistant_response = response_message["content"]
                    conversation.append({"role": "assistant", "content": assistant_response})
                break
            except Exception as e:
                if i>3: 
                    break
                print("Exception as below, will retry\n", str(e))

        return request_agent_change, conversation, assistant_response

