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
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
MAX_ERROR_RUN = 3
MAX_RUN_PER_QUESTION =10
MAX_QUESTION_TO_KEEP = 3
MAX_QUESTION_WITH_DETAIL_HIST = 1

emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine1 =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT1")
chat_engine2 =os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT2")
sqllite_db_path= os.environ.get("SQLITE_DB_PATH","data/northwind.db")
engine = create_engine(f'sqlite:///{sqllite_db_path}') 
client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT"),
)
max_conversation_len = 5  # Set the desired value of k


emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
#azcs implementation
searchservice = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
service_endpoint=f"https://{searchservice}.search.windows.net/"
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") 
key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 

# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

credential = AzureKeyCredential(key)
azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)


def search_memory(search_query):

    vector = VectorizedQuery(vector=get_embedding(search_query), k_nearest_neighbors=3, fields="questionVector")
    # print("search query: ", search_query)

    results = azcs_search_client.search(  
        search_text=search_query,  
        vector_queries= [vector],
        query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
        select=["code","answer"],
        top=2
    )  
    text_content =""
    for result in results:  
        text_content += f"code solution\n: {result['code']}\nAnswer:\n {result['answer']}\n"
    # print("text_content", text_content)
    return text_content

###Sematic caching implementation
if os.getenv("USE_SEMANTIC_CACHE") == "True":
    cache_index_name = os.getenv("CACHE_INDEX_NAME")
    cache_index_name= cache_index_name.strip('"')
    azcs_semantic_cache_search_client = SearchClient(service_endpoint, cache_index_name, credential=credential)

def add_to_cache(question, code, answer):
    experience = {
                 "id" : str(uuid.uuid4()),
                 "question" : question,
                 "code" : code,
                 "questionVector" : get_embedding(question),
                "answer" : answer
              }
    azcs_search_client.upload_documents(documents = [experience])
def get_cache(question):
    vector = VectorizedQuery(vector=get_embedding(question), k_nearest_neighbors=3, fields="questionVector")
    # print("search query: ", search_query)

    results = azcs_search_client.search(  
        search_text=question,  
        vector_queries= [vector],
        # query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
        select=["question","code","answer"],
        top=2
    )  
    text_content =""
    for result in results:  
        if result['@search.score']>= float(os.getenv("SEMANTIC_HIT_THRESHOLD")):
            text_content += f"question: {result['question']}\ncode solution\n: {result['code']}\nAnswer:\n {result['answer']}\n"
        else:
            print("No cache hit at: ", result['@search.score'])
    return text_content


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

def execute_sql_query(sql_query, limit=100):  
    result = pd.read_sql_query(sql_query, engine)
    result = result.infer_objects()
    for col in result.columns:  
        if 'date' in col.lower():  
            result[col] = pd.to_datetime(result[col], errors="ignore")  

    # result = result.head(limit)  # limit to save memory  
    # st.write(result)
    return result
orders_sample = execute_sql_query("SELECT * FROM orders LIMIT 1").to_markdown(index=False)
customers_sample = execute_sql_query("SELECT * FROM customers limit 1").to_markdown(index=False)
products_sample = execute_sql_query("SELECT * FROM products limit 1").to_markdown(index=False)
order_details_sample = execute_sql_query("SELECT * FROM [Order Details] limit 1").to_markdown(index=False)
employees_sample = execute_sql_query("SELECT * FROM employees limit 1").to_markdown(index=False)
# shippers_sample = execute_sql_query("SELECT * FROM shippers limit 1").to_markdown(index=False)
# suppliers_sample = execute_sql_query("SELECT * FROM suppliers limit 1").to_markdown(index=False)
# categories_sample =execute_sql_query("SELECT * FROM categories LIMIT 1").to_markdown(index=False)
# territories_sample =execute_sql_query("SELECT * FROM territories LIMIT 1").to_markdown(index=False)
# employeeTerritories_sample =execute_sql_query("SELECT * FROM employeeTerritories LIMIT 2").to_markdown(index=False)
# customerDemographics_sample =execute_sql_query("SELECT * FROM customerDemographics LIMIT 2").to_markdown(index=False)


today = pd.Timestamp.today()
#format today's date
today = today.strftime("%Y-%m-%d")
CODER1 = f"""
You are an expert data analyst with great expertise in data analysis, visualization, SQL and Python to answer question from business users.
Today's date is {today}
Data is stored in a SQLITE database.
Sample data is provided below for your reference.
The orders table: {orders_sample}
The customers table: {customers_sample}
The [Order Details] table: {order_details_sample}
The products table: {products_sample}

Data query, transformation and visualization all need to happen via a Python interface provided to you.
First, you interact with user to understand their requirement. Clarify if needed.
If the question is complex, apply best practices in business analytics to break it down into smaller parts and solve each part separately. While doing so, explain your thought process to the user.
Finally present your findings to the user in a clear and concise manner. 
Use visualization when appropriate to best communicate your answer.
Before applying any filter conditions in your queries, please first sample the database to understand the data distribution, especially the case sensitivity and format of key values. For instance, if you're considering using 'isCanceled' as a filter condition, verify whether the database stores this value as 'True', 'true', or in another variation. Adjust your query accordingly to match the exact data representation in the database. Use this approach for all attributes to ensure accurate query results.  
"""
CODER2= """
You are an expert data analyst with great expertise in data analysis, visualization, SQL and Python to answer question from business users.
Today's date is {today}
Data is stored in a SQLITE database.
Data query, transformation and visualization all need to happen via a Python interface provided to you.
First, you interact with user to understand their requirement. Clarify if needed.
You are provided with similiar answered questions with solutions.
Determine that the reference solutions can provide sufficient context for you to answer the new question.
If yes, go ahead to implement the solution.
If no, use the retrieve additional context function to get more information to be able to answer the question.
Use visualization when appropriate to best communicate your answer.

"""


def create_or_update_action_plan(new_or_updated_plan):
    return new_or_updated_plan
def update_notebook(existing_content, new_content):  
    """  
    Update the existing notebook content with new content.  
  
    :param existing_content: The existing content of the notebook.  
    :param new_content: The new content to add to the notebook.  
    :return: The updated notebook content.  
    """  
    # Identify the start of the notebook section  
    notebook_start = existing_content.find('## Notebook:')  
      
    # Check if the notebook section is found  
    if notebook_start == -1:  
        # The notebook section doesn't exist, return the original content  
        return existing_content  
      
    # Extract the content before and after the notebook section  
    before_notebook = existing_content[:notebook_start]  
      
    updated_content = before_notebook.strip() +"\n## Action plan:\n"+ new_content.strip()    
      
    return updated_content  



def execute_python_code(assumptions, goal,python_code,execution_context):

    def execute_sql_query(sql_query, limit=100):  
        result = pd.read_sql_query(sql_query, engine)
        result = result.infer_objects()
        for col in result.columns:  
            if 'date' in col.lower():  
                result[col] = pd.to_datetime(result[col], errors="ignore")  

        # result = result.head(limit)  # limit to save memory  
        # st.write(result)
        return result
  
    def reduce_dataframe_size(df):  
        max_str_length = 100  
        max_list_length = 3
        
        reduced_df = pd.DataFrame()  
        
        for column in df.columns:  
            if df[column].dtype == object or df[column].dtype == str:  
                reduced_df[column] = df[column].apply(lambda x: reduce_cell(x, max_str_length, max_list_length))  
            else:  
                reduced_df[column] = df[column]  
        
        return reduced_df  
  
    def reduce_cell(cell, max_str_length, max_list_length):  
        try:  
            data = json.loads(cell)  
            if isinstance(data, list):  
                data = truncate_list(data, max_list_length)  
            return json.dumps(data)  
        except (json.JSONDecodeError, TypeError):  
            return str(cell)[:max_str_length]  
    
    def truncate_list(lst, max_list_length):  
        truncated = lst[:max_list_length]  
        for i, item in enumerate(truncated):  
            if isinstance(item, dict):  
                truncated[i] = truncate_dict(item, max_list_length)  
            elif isinstance(item, list):  
                truncated[i] = truncate_list(item, max_list_length)  
        return truncated  
    
    def truncate_dict(dct, max_list_length):  
        for key, value in dct.items():  
            if isinstance(value, list):  
                dct[key] = truncate_list(value, max_list_length)  
            elif isinstance(value, dict):  
                dct[key] = truncate_dict(value, max_list_length)  
        return dct  
    
    def show_to_user(data):
        # question = st.session_state['question']
        st.session_state['data'] = data
        question = "Describe this graph in detail"
        for session_item in st.session_state:
            if 'data_from_display' in session_item or 'comment_on_graph' in session_item:  
                del st.session_state[session_item]  
        img_folder =  str(uuid.uuid4())
        os.makedirs(img_folder, exist_ok=True)
        image_path=os.path.join(img_folder,"plot.jpg")
        if st.session_state['show_internal_thoughts']:
            st.write("Goal: "+goal)
            st.write("Assumptions: \n"+assumptions)

        try:
            if type(data) is PlotlyFigure:
                st.plotly_chart(data)
                comment ="The graph for the data is shown to the user."
                if st.session_state['use_gpt4v']:  
                    write_image(data, image_path)
                    comment = comment_on_graph(question, image_path)
                    comment = "the graph is displayed and this is the description of the graph: \n" + comment + "\n"
                st.session_state['comment_on_graph'] = comment

            elif type(data) is MatplotFigure:
                st.pyplot(data)

                plt.savefig(image_path)
                comment = comment_on_graph(question, image_path)
                
                st.session_state['comment_on_graph'] = comment

            elif type(data) is pd.DataFrame:
                data = data.head(30)
                data = reduce_dataframe_size(data)
                st.dataframe(data)
                st.session_state['data_from_display_'+str(uuid.uuid4())] = data.to_markdown(index=False, disable_numparse=True)
            else:
                st.write(data)
                st.session_state['data_from_display'] = str(data)
        except Exception as e:
            print("Error in generating commment on the graph: ", e)
        finally:
            shutil.rmtree(img_folder)
    if 'execute_sql_query' not in execution_context:
        execution_context['execute_sql_query'] = execute_sql_query 
    if 'show_to_user' not in execution_context: 
        execution_context['show_to_user'] = show_to_user  

    # Define a context manager to redirect stdout and stderr  
    @contextlib.contextmanager  
    def captured_output():  
        new_out, new_err = StringIO(), StringIO()  
        old_out, old_err = sys.stdout, sys.stderr  
        try:  
            sys.stdout, sys.stderr = new_out, new_err  
            yield sys.stdout, sys.stderr  
        finally:  
            sys.stdout, sys.stderr = old_out, old_err  
  
    # Use the context manager to capture output  
    with captured_output() as (out, err):  
        try:  
            exec(python_code, execution_context)
            
        except Exception as e:  
            if hasattr(e, 'message'):
                print("with message in exception")
                print(f"{type(e)}: {e.message}", file=sys.stderr)  
            else:
                print(f"{type(e)}: {e}", file=sys.stderr)  

    
    # Retrieve the captured output and errors  
    stdout = out.getvalue()  
    stderr = err.getvalue()  

    new_input=""
    if len(stdout)>0:
        new_input +="\n"+ stdout 
        print(new_input)        
        return execution_context, new_input

    if len(stderr)>0:
        new_input +="\n"+stderr
        print(new_input)
        print(python_code)
        return execution_context, new_input
    data_display=""
    for session_item in st.session_state:
        if 'data_from_display' in session_item:  
            data_display +="\n" + st.session_state[session_item]
    if len(data_display)>0:
        return execution_context, data_display
    if 'comment_on_graph' in st.session_state:
        return execution_context, str(st.session_state['comment_on_graph'])
    else:
        return execution_context, "The graph for the data is displayed to the user."
    



def resolve_entities(business_question):
    if 'VINET' in business_question:
        return business_question.replace("VINET", "VINET customer")
    return "Cannot resolve the entities in the question. Please clarify with the customer."
def get_additional_context():
    pass

CODER_AVAILABLE_FUNCTIONS1 = {
            "execute_python_code": execute_python_code,
        } 


CODER_FUNCTIONS_SPEC1= [  
    
    {
        "type":"function",
        "function":{

        "name": "execute_python_code",
        "description": "A special python interface that can run data analytical python code against the SQL database and data visualization with plotly. Do not use from pandas.io.json import json_normalize use from pandas import json_normalize instead",
        "parameters": {
            "type": "object",
            "properties": {
                "assumptions": {
                    "type": "string",
                    "description": "List of assumptions you made in your code."
                },
                "goal": {
                    "type": "string",
                    "description": "description of what you hope to achieve with this python code snippset. The description should be in the same language as the question asked by the user."
                },

                "python_code": {
                    "type": "string",
                    "description": "Complete executable python code. You are provided with following utility python functions to use INSIDE your code \n 1. execute_sql_query(sql_query: str) a function to execute SQL query against the SQLITE database to retrieve data you need. This execute_sql_query(sql_query: str) function returns a pandas dataframe that you can use to perform any data analysis and visualization. Be efficient, avoid using Select *, instead select specific column names if possible\n 2. show_to_user(data): a util function to display the data analysis and visualization result from this environment to user. This function can take a pandas dataframe or plotly figure as input. For example, to visualize a plotly figure, the code can be ```fig=px.line(some_df)\n show_to_user(fig)```. Only use plotly for graph visualization. Remember, only use show_to_user if you want to display the data to the user. If you want to observe any data for yourself, use print() function instead "
                },


            },
            "required": ["assumptions", "goal","python_code" ],
        },

    }
    },

]  

CODER_FUNCTIONS_SPEC2= [{
        "type":"function",
        "function":{

        "name": "get_additional_context",
        "description": "Current context information is not sufficient, get additional context to be able to write code to answer the question",
        },

    }]
CODER_FUNCTIONS_SPEC2 += CODER_FUNCTIONS_SPEC1

CODER_AVAILABLE_FUNCTIONS2 = CODER_AVAILABLE_FUNCTIONS1.copy()
CODER_AVAILABLE_FUNCTIONS2["get_additional_context"] = get_additional_context


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
    for session_item in st.session_state:
        if 'data_from_display' in session_item or 'comment_on_graph' in session_item:  
            del st.session_state[session_item] 


class Smart_Agent():
    """
    """

    def __init__(self, persona,functions_spec, functions_list, name=None, init_message=None, engine =chat_engine2):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.conversation =  init_hist
        self.persona = persona
        self.engine = engine
        self.persona ="coder2"
        self.name= name

        self.functions_spec = functions_spec
        self.functions_list= functions_list
    def switch_persona(self, similiar_question=None):
            
            if self.persona == "coder1" or similiar_question is not None:
                if similiar_question is not None:
                    new_system_message = {"role": "system", "content": CODER2+"here are similiar answered questions with solutions: \n"+similiar_question}
                    self.conversation[0]= new_system_message
                    self.engine = chat_engine2
                    self.persona = "coder2"
                    self.functions_spec = CODER_FUNCTIONS_SPEC2
                    self.functions_list = CODER_AVAILABLE_FUNCTIONS2
                    if self.engine == chat_engine2:
                        print("Giving similiar solutions context to coder2")
                    else:
                        print("Switching persona to coder2 from coder1")
            elif self.persona == "coder2":
                print("Switching persona to coder1")
                new_system_message = {"role": "system", "content": CODER1}
                self.conversation[0]= new_system_message
                self.engine = chat_engine1
                self.persona = "coder1"
                self.functions_spec = CODER_FUNCTIONS_SPEC1
                self.functions_list = CODER_AVAILABLE_FUNCTIONS1


    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def run(self, user_input, conversation=None, stream = False, ):
        if user_input is None: #if no input return init message
            return self.conversation, self.conversation[1]["content"]
        if conversation is not None: #if no history return init message
            self.conversation = conversation
        similiar_question = get_cache(user_input)
        if self.engine == chat_engine1:
            if len(similiar_question)>0:
                self.switch_persona(similiar_question)
        else:
            if len(similiar_question)>0:
                self.switch_persona(similiar_question) #updating coder 2 with similiar questions
            else:
                self.switch_persona() #no similiar questions, switch to coder 1
        
        
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
            

            # print("assistant response: ", response_message.content)
            # Step 2: check if GPT wanted to call a function
            if  tool_calls:
                # print("Tool calls: ")
                self.conversation.append(response_message)  # extend conversation with assistant's reply
                for tool_call in tool_calls:
                    function_name = tool_call.function.name

                    print("Recommended Function call:")
                    print(function_name)
                    print()
                    if function_name == "get_additional_context":
                        self.switch_persona()
                        reset_history_to_last_question(self.conversation)
                        run_count=0
                        continue

                    # Step 3: call the function
                    # Note: the JSON response may not always be valid; be sure to handle errors
                                    
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
                    if function_name == "execute_python_code":
                        function_args["execution_context"] = execution_context

                    if check_args(function_to_call, function_args) is False:
                        self.conversation.pop()
                        break
                    if function_name == "execute_python_code":
                        execution_context, function_response = function_to_call(**function_args)
                        if "data" in st.session_state:
                            data[tool_call.id] = st.session_state['data']
                        if "error" in function_response:
                            execution_error_count+=1
                        else:
                            code = function_args["python_code"]


                    else:
                        function_response = str(function_to_call(**function_args))
                                     
                    # print("Output of function call:")
                    # print("length of function_response", len(function_response))
                    print()
                    if function_name == "message_user" or function_name =="message_team": #special case when coder finished the code execution and ready to respond to user or the coder needs to clarify with context preparer
                        return function_response

                
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