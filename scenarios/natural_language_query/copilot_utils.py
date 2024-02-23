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
import pyodbc
from openai import AzureOpenAI
from sqlalchemy import create_engine  
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
import streamlit as st
from plotly.io import write_image
import matplotlib.pyplot as plt

from io import StringIO
import shutil
from urllib import parse
import sys
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryCaptionResult,
    QueryAnswerResult,
    SemanticErrorMode,
    SemanticErrorReason,
    SemanticSearchResultsType,
    QueryType,
    VectorizedQuery,
    VectorQuery,
    VectorFilterMode,    
)
import uuid
from tenacity import retry, wait_random_exponential, stop_after_attempt  
from langchain.utilities import BingSearchAPIWrapper
import pandas as pd
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
# from openai.embeddings_utils import get_embedding, cosine_similarity
import inspect
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
gpt_4_engine = os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT")
sqllite_db_path= os.environ.get("SQLITE_DB_PATH","data/northwind.db")
engine = create_engine(f'sqlite:///{sqllite_db_path}') 
client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version="2023-12-01-preview",
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
)
max_conversation_len = 5  # Set the desired value of k


def load_data_from_json(file_path="data/metadata.json"):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data
def message_coder(context, business_question):
    message= f"Hi coder, Please write a code to answer the following question: {business_question} \n\nContext: {context}"
    print("message to coder: \n", message)
    coder = Smart_Agent(persona=CODER,functions_list=CODER_AVAILABLE_FUNCTIONS, functions_spec=CODER_FUNCTIONS_SPEC, engine=gpt_4_engine)
    return coder.run(message, stream=False)

def message_team(message):
    return f"This is internal team message from your coder: {message}"
def message_user(message):
    return f"{message}"

def get_scenarios_md():
    data = load_data_from_json()

    # Extract values from the loaded data
    analytic_scenarios = data.get("analytic_scenarios", {})
    scenario_list = [(scenario[0], scenario[1]['description']) for scenario in analytic_scenarios.items()]
    # create  scenario_list_md which is the a markdown table with column headers 'Scenario' and 'Description' from scenario_list
    scenario_list_md = ""
    for scenario in scenario_list:
        scenario_list_md += f"| {scenario[0]} | {scenario[1]} |\n"
    #add headers 'Scenario' and 'Description' to scenario_list_md
    scenario_list_md = f"| Scenario | Description |\n| --- | --- |\n{scenario_list_md}"
    return scenario_list_md

# def get_scenario_names(business_question):
#     response = client.chat.completions.create(
#         model=chat_engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
#         messages=[{"role": "system", "content": CONTEXT_PREPARER}, {"role": "user", "content": business_question}],
#     response_format={"type": "json_object"}
    
#     )
    
#     response_message = response.choices[0].message.content.strip()
#     print("response_message: ", response_message)
#     scenario_list = json.loads(response_message)["scenarios"]
#     scenario_list = [scenario["scenario_name"] for scenario in scenario_list]

#     return scenario_list
@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def retrieve_context(business_question):
    response = client.chat.completions.create(
        model=chat_engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
        messages=[{"role": "system", "content": CONTEXT_PREPARER}, {"role": "user", "content": business_question}],
    response_format={"type": "json_object"}
    
    )
    
    response_message = response.choices[0].message.content.strip()
    print("response_message: ", response_message)
    scenario_names = json.loads(response_message)["scenarios"]
    scenario_names = [scenario["scenario_name"] for scenario in scenario_names]


    data = load_data_from_json()
    # Extract values from the loaded data
    analytic_scenarios = data.get("analytic_scenarios", {})
    scenario_list = [scenario[0] for scenario in analytic_scenarios.items()]
    if not set(scenario_names).issubset(set(scenario_list)):
        raise Exception("You provided invalid scenario name(s), please check and try again")
    scenario_tables = data.get("scenario_tables", {})
    scenario_context = "Following tables might be relevant to the question: \n"
    all_tables = data.get("tables", {})
    all_relationships = data.get("table_relationships", {})
    all_relationships = {(relationship[0], relationship[1]):relationship[2] for relationship in all_relationships}
    tables = set()
    for scenario_name in scenario_names:
        tables.update(scenario_tables.get(scenario_name, []))
    for table in tables:
        scenario_context += f"- table_name: {table} - description: {all_tables[table]['description']} - columns: {all_tables[table]['columns']}\n"
    table_pairs = [(table1, table2) for table1 in tables for table2 in tables if table1 != table2]
    relationships = set()
    for table_pair in table_pairs:
        relationship = all_relationships.get(table_pair, None)
        if relationship:
            relationships.add((table_pair[0], table_pair[1], relationship)) 
    
    scenario_context += "\n"
    scenario_context += "\nTable relationships: \n"
    for relationship in relationships:
        scenario_context += f"- {relationship[0]}, {relationship[1]}:{relationship[2]}\n"
    

    scenario_context += "\nFollowing rules might be relevant: \n"
    for scenario_name in scenario_names:
        scenario_context += f"- {scenario_name}: {str(analytic_scenarios[scenario_name]['rules'])}\n"
    return scenario_context
def comment_on_graph(question, image_path="plot.jpg"):
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Path to your image

    # Getting the base64 string
    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
    model=os.environ.get("AZURE_OPEN_AI_VISION_DEPLOYMENT"),
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": question},
            {
            "type": "image_url",
            "image_url": {
                "url":  f"data:image/jpeg;base64,{base64_image}",
            },
            },
        ],
        }
    ],
    max_tokens=500,
    )

    return response.choices[0].message.content
CONTEXT_PREPARER = f"""
You are an AI assistant that helps people find information. 
You are given a business question and you need to identify which one or several business analytic scenario(s) below are relevant to the question.
<<analytic_scenarios>>
{get_scenarios_md()}
<</analytic_scenarios>>
Output your response in json format with the following structure:   
{{
    "scenarios": [
        {{
            "scenario_name": "...", # name of the scenario. 
        }}
    ]
}}

"""
# After you have discovered the information you need, forward it to the coder.
# Only provide what you discover from the tools. Do not make up any information.

#tools: get_scenarios, retrieve_context, find_similar_cases, resolve_entities, mess

CODER = f"""
You are a creative AI assistant with expertise in data analysis,visualization, SQL and Python to answer question from your business user.
Data is stored in a SQLITE database. In order to answer the question, you need to query the data then apply business rules to compute business metrics which must all happen using the Python interface.
You do not have knowlwege about database schema nor business rules in your mind but you can discover them by using the tools available to you.
With that, start by interacting with the user to understand their business question then use your talent to find answer for the question.
Clarify with the user if needed.
Note that customer does not have knowlege about the database, avoid asking them technical questions. 
If problem is complex, solve it in multiple steps.
Show off your visualization talent when appropriate to best communicate your answer.

"""
# Provide feedback to your team when you think their inputs are not sufficient for you to create the solution.

#function for coder: execute_python_code, message_to_team, message_to_user


service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding


credential = AzureKeyCredential(key)
azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)



def find_similar_cases(business_query, topk=3):
    vector_query = VectorizedQuery(vector=get_embedding(business_query), k_nearest_neighbors=3, fields="questionVector")

    print("business_query: ", business_query)
    results = azcs_search_client.search(  
        search_text=business_query,  
        vector_queries= [vector_query],
        query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
        select=["question","sql_query"],
        top=topk
    )  
    text_content =""

    for result in results:  
        text_content += f"\n\nQuestion: {result['question']}\nSQL query used: {result['sql_query']}"

    return text_content


###Sematic caching implementation
if os.getenv("USE_SEMANTIC_CACHE") == "True":
    cache_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    azcs_semantic_cache_search_client = SearchClient(service_endpoint, cache_index_name, credential=credential)

def add_to_cache(question, sql_query):
    print("adding to cache: ", question, sql_query)
    question_embeddings = get_embedding(question)
    # sql_embeddings = get_embedding(sql_query)
    doc = {
                 "id" : str(uuid.uuid4()),
                 "question" : question,
                 "sql_query" : sql_query,
                 "questionVector" : question_embeddings,
                # "sqlVector" : sql_embeddings
              }
    azcs_semantic_cache_search_client.upload_documents(documents = [doc])
    print("added to cache: ", question, sql_query)



def execute_python_code(python_code, goal, execution_context):
    print("goal: ", goal)

    def execute_sql_query(sql_query, limit=100):  
        result = pd.read_sql_query(sql_query, engine)
        result = result.infer_objects()
        for col in result.columns:  
            if 'date' in col.lower():  
                result[col] = pd.to_datetime(result[col], errors="ignore")  

        if limit is not None:  
            result = result.head(limit)  # limit to save memory  
        # st.write(result)
        return result

    def display(data):
        # question = st.session_state['question']
        st.session_state['data'] = data
        question = "Describe this graph in detail"
        if 'data_from_display' in st.session_state:  
            del st.session_state['data_from_display']  
        if 'comment_on_graph' in st.session_state:  
            del st.session_state['comment_on_graph']  
        img_folder =  str(uuid.uuid4())
        os.makedirs(img_folder, exist_ok=True)
        image_path=os.path.join(img_folder,"plot.jpg")
        try:
            if type(data) is PlotlyFigure:
                st.plotly_chart(data)

                write_image(data, image_path)
                comment = comment_on_graph(question, image_path)
                comment = "the graph is displayed and this is what you see: \n" + comment + "\n"
                st.session_state['comment_on_graph'] = comment

            elif type(data) is MatplotFigure:
                st.pyplot(data)

                plt.savefig(image_path)
                comment = comment_on_graph(question, image_path)
                
                st.session_state['comment_on_graph'] = comment

            elif type(data) is pd.DataFrame:
                st.dataframe(data)
                st.session_state['data_from_display'] = data.to_markdown(index=False)
            else:
                print("data type not known \n", data)
        finally:
            shutil.rmtree(img_folder)
    if 'execute_sql_query' not in execution_context:
        execution_context['execute_sql_query'] = execute_sql_query 
    if 'display' not in execution_context: 
        execution_context['display'] = display  

    st.write("Goal: "+goal)
    # st.code(python_code)
    
    # old_stdout = sys.stdout
    # sys.stdout = mystdout = StringIO()
    new_input=""
    try:
        exec(python_code, execution_context)
        # sys.stdout = old_stdout
        # std_out = str(mystdout.getvalue())
        # if len(std_out)>0:
        #     new_input +="\n"+ std_out 
        #     print(new_input)                  
    except Exception as e:
        new_input +="\Encounter following error, please fix the bug and give updated code\n"+str(e)+"\n"
        # print(new_input)
        return execution_context, new_input
    if 'data_from_display' in st.session_state:
        return execution_context, str(st.session_state['data_from_display'])
    elif 'comment_on_graph' in st.session_state:
        # print("comment returned from comment on graph ", st.session_state['comment_on_graph'])
        return execution_context, str(st.session_state['comment_on_graph'])
    else:
        return execution_context, "No graph or data was displayed, did you forget to call display(data) function?"
    



def resolve_entities(business_question):
    if 'VINET' in business_question:
        return business_question.replace("VINET", "VINET customer")
    return "Cannot resolve the entities in the question. Please clarify with the customer."

CONTEXT_PREPARER_AVAILABLE_FUNCTIONS = {
            "get_scenarios": get_scenarios_md,
            "retrieve_context": retrieve_context,
            # "find_similar_cases":find_similar_cases ,
            # "resolve_entities": resolve_entities,


        } 
CODER_AVAILABLE_FUNCTIONS = {
            "execute_python_code": execute_python_code,
            "retrieve_context": retrieve_context,

        } 


CONTEXT_PREPARER_FUNCTIONS_SPEC= [  
    {
        "type":"function",
        "function":{

        "name": "retrieve_context",
        "description": "Look up business rules and table schemas for one or more business analytic scenarios",
        "parameters": {
            "type": "object",
            "properties": {
                "scenario_names": {
                    "type": "string",
                    "description": "comma separated list of valid scenarios names" 
                }

            },
            "required": ["scenario_names"],
        },
    }
    },

    # {
        # "type":"function",
        # "function":{
        # "name": "resolve_entities",
        # "description": "When customer question contains values that are not clear which business entities they belong to, this function can be used to resolve the entities. For example, if the customer asks 'What is the total sales for Raclette?', the function will rephrase the question into 'What is the total sales for product Raclette?' as it understand Raclette is a product. This function should only be used if retrieve_context is used",
        # "parameters": {
        #     "type": "object",
        #     "properties": {
        #         "business_question": {
        #             "type": "string",
        #             "description": "Rephrased customer's question that is clear and concise"
        #         }
        #     },
        #     "required": ["business_question"],
        # },
    # }
    # },

    # {
    #     "type":"function",
    #     "function":{

    #     "name": "find_similar_cases",
    #     "description": "Return similiar questions from the answered questions pool and SQL queries used to infer schema and business rules to apply for your question. This should be used first before resorting get_scenarios and retrieve_context functions",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "business_query": {
    #                 "type": "string",
    #                 "description": "Complete and clear business question" 
    #             }

    #         },
    #         "required": ["business_query"],
    #     },
    # }
    # },


    
]  

CODER_FUNCTIONS_SPEC= [  
    
    {
        "type":"function",
        "function":{

        "name": "execute_python_code",
        "description": "A special python interface that can run data analytical python code against the SQL database and data visualization with plotly. Data and visualization object can only be observed using display() function inside your code. Python's print function will not work",
        "parameters": {
            "type": "object",
            "properties": {
                "python_code": {
                    "type": "string",
                    "description": "Complete executable python code with display() function to display and observe output. You are provided with following utility python functions to use INSIDE your code \n 1. execute_sql_query(sql_query: str) a function to execute SQL query against the SQLITE database to retrieve data you need. This execute_sql_query(sql_query: str) function returns a pandas dataframe that you can use to perform any data analysis and visualization.\n 2. display(data): a util function to display the data analysis and visualization result from this environment. This function can take a pandas dataframe or plotly figure as input. For example, to visualize a plotly figure, the code can be ```fig=px.line(some_df)\n display(fig)```. Only use plotly for graph visualization"
                },
                "goal": {
                    "type": "string",
                    "description": "description of what you hope to achieve with this python code snippset"
                }

            },
            "required": ["python_code", "goal"],
        },

    }
    },
    {
        "type":"function",
        "function":{

        "name": "retrieve_context",
        "description": "retrieve business rules and table schemas that are relevant to the customer's question",

        "parameters": {
            "type": "object",
            "properties": {
                "business_question": {
                    "type": "string",
                    "description": "Rephrased business question in clear and concise form" 
                }


            },
            "required": ["business_question"],
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

class Smart_Agent():
    """
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
    def run(self, user_input, conversation=None, stream = False):
        if user_input is None: #if no input return init message
            return self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        i=0
        query_used = None
        data ={}
        execution_context={}
        while True:
            response = client.chat.completions.create(
                model=self.engine, # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                messages=conversation,
            tools=self.functions_spec,
            tool_choice='auto'
            
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
                        print(("Function " + function_name + " does not exist, retrying"))
                        conversation.pop()
                        break
                    function_to_call = self.functions_list[function_name]
                    
                    # verify function has correct number of arguments
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(e)
                        conversation.pop()
                        break
                    if function_name == "execute_python_code":
                        function_args["execution_context"] = execution_context

                    if check_args(function_to_call, function_args) is False:
                        conversation.pop()
                        break
                    if function_name == "execute_python_code":
                        execution_context, function_response = function_to_call(**function_args)
                        if "data" in st.session_state:
                            data[tool_call.id] = st.session_state['data']
                        if "fix the bug" in function_response:
                            print(function_response)
                            print("bug in the code, retrying")
                            conversation.pop()
                            break
                            # continue

                    else:
                        function_response = str(function_to_call(**function_args))
                                     
                    print("Output of function call:")
                    print(function_response)
                    print()
                    if function_name == "message_user" or function_name =="message_team": #special case when coder finished the code execution and ready to respond to user or the coder needs to clarify with context preparer
                        return function_response

                
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

        if not stream:
            conversation.append(response_message)
            assistant_response = response_message.content
            # conversation.append({"role": "assistant", "content": assistant_response})

        else:
            assistant_response = response_message

        return stream,query_used, conversation, assistant_response, data