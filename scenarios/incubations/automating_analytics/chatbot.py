import openai
from openai import AzureOpenAI
import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine  
import pandas as pd
import json
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

if os.getenv('WEBSITE_SITE_NAME') is None:
    env_path = Path('.') / 'secrets.env'
    load_dotenv(dotenv_path=env_path)


token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )

def load_setting(setting_name, session_name,default_value=''):  
    """  
    Function to load the setting information from session  
    """  
    if session_name not in st.session_state:  
        if os.environ.get(setting_name) is not None:
            st.session_state[session_name] = os.environ.get(setting_name)
        else:
            st.session_state[session_name] = default_value  


load_setting("AZURE_OPENAI_CHATGPT_DEPLOYMENT","chatgpt","gpt-35-turbo")  
load_setting("AZURE_OPENAI_GPT4_DEPLOYMENT","gpt4","gpt-35-turbo")  
load_setting("AZURE_OPENAI_ENDPOINT","endpoint","https://resourcenamehere.openai.azure.com/")  
load_setting("AZURE_OPENAI_API_KEY","apikey")  

openai.api_type = "azure"
openai.api_version = "2023-03-15-preview" 
#openai.api_key = st.session_state.apikey
openai.api_base = st.session_state.endpoint


client = AzureOpenAI(
  #api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT"),
  azure_ad_token_provider=token_provider
)

def get_table_schema(sql_engine='sqlite'):
    # Define the SQL query to retrieve table and column information 
    if sql_engine== 'sqlserver': 
        sql_query = """  
        SELECT C.TABLE_NAME, C.COLUMN_NAME, C.DATA_TYPE, T.TABLE_TYPE, T.TABLE_SCHEMA  
        FROM INFORMATION_SCHEMA.COLUMNS C  
        JOIN INFORMATION_SCHEMA.TABLES T ON C.TABLE_NAME = T.TABLE_NAME AND C.TABLE_SCHEMA = T.TABLE_SCHEMA  
        WHERE T.TABLE_TYPE = 'BASE TABLE'  
        """  
    elif sql_engine=='sqlite':
        sql_query = """    
        SELECT m.name AS TABLE_NAME, p.name AS COLUMN_NAME, p.type AS DATA_TYPE  
        FROM sqlite_master AS m  
        JOIN pragma_table_info(m.name) AS p  
        WHERE m.type = 'table'  
        """  
    else:
        raise Exception("unsupported SQL engine, please manually update code to retrieve database schema")

    # Execute the SQL query and store the results in a DataFrame  
    engine = create_engine(f'sqlite:///data/northwind.db') 
    result = pd.read_sql_query(sql_query, engine)
    result = result.infer_objects()
    for col in result.columns:  
        if 'date' in col.lower():  
            result[col] = pd.to_datetime(result[col], errors="ignore")  
    df = result 
    output=[]
    # Initialize variables to store table and column information  
    current_table = ''  
    columns = []  
    
    # Loop through the query results and output the table and column information  
    for index, row in df.iterrows():
        if sql_engine== 'sqlserver': 
            table_name = f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"  
        else:
            table_name = f"{row['TABLE_NAME']}" 

        column_name = row['COLUMN_NAME']  
        data_type = row['DATA_TYPE']   
        if " " in table_name:
            table_name= f"[{table_name}]" 
        column_name = row['COLUMN_NAME']  
        if " " in column_name:
            column_name= f"[{column_name}]" 

        # If the table name has changed, output the previous table's information  
        if current_table != table_name and current_table != '':  
            output.append(f"table: {current_table}, columns: {', '.join(columns)}")  
            columns = []  
        
        # Add the current column information to the list of columns for the current table  
        columns.append(f"{column_name} {data_type}")  
        
        # Update the current table name  
        current_table = table_name  
    
    # Output the last table's information  
    output.append(f"table: {current_table}, columns: {', '.join(columns)}")
    output = "\n ".join(output)
    return output


def execute_external_api(category: str):
    # to do 
    # call external api
    top_skus = []
    return top_skus

def execute_sql_query(sql_query: str):
    try:
        engine = create_engine(f'sqlite:///data/northwind.db') 
        result = pd.read_sql_query(sql_query, engine)
        result = result.infer_objects()
        return json.dumps(result.to_dict(orient='records'))
    except Exception as e:
        return f"An error occurred: {str(e)}"
   #st.session_state.messages.append({"role": "user", "content": json.dumps(result.to_dict(orient='records'))})
   #return result


available_tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "Execute a sql query on the SQLite Northwind database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The SQL query to execute.",
                    },
                },
                "required": ["sql_query"],
                "additionalProperties": False,
            }
    }
    
},
{
        "type": "function",
        "function": {
            "name": "execute_external_api",
            "description": "Execute an external API call to get the top SKUs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The category of the SKUs to retrieve.",
                    },
                },
                "required": ["category"],
                "additionalProperties": False,
            }
    }
    
}


]

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

st.title("💬 Chatbot")
st.caption("🚀 A Streamlit chatbot powered by OpenAI")


sql_schema = get_table_schema("sqlite")

system_message = """
You are SQL query assistant who can generate a SQL query on SQLite Northwind database based on the user input.
If you cannot generate the SQL query, state that you can only answer questions about Northwind Database.
Use the supplied tools to assist the user. Use the SQL schema to generate the SQL query.
SQL Schema:
{sql_schema}
"""

assistant_message = """
I can help you generate a SQL query on the SQLite Northwind database. 
"""

if "messages" not in st.session_state:
    st.session_state["messages"] = [
            {"role": "system", "content": system_message },
            {"role": "assistant", "content": assistant_message }
        ]

for msg in st.session_state.messages:
    if msg["role"] == "system":
        pass
    else:
        st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    #if not openai_api_key:
    #    st.info("Please add your OpenAI API key to continue.")
    #    st.stop()

    #client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    response = client.chat.completions.create(
        model=st.session_state.gpt4, 
        messages=st.session_state.messages,
        tool_choice="auto",
        tools=available_tools
    )
    msg = response.choices[0].message
    if msg.content:
        st.session_state.messages.append({"role": "assistant", "content": msg.content})
    
    #tool_call = response.choices[0].message.tool_calls[0]
    if response.choices[0].message.tool_calls:
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "execute_sql_query":
                function_args = json.loads(tool_call.function.arguments)
                print(f"Function arguments: {function_args}")  
                sql_response = execute_sql_query(
                    sql_query=function_args.get("sql_query")
                )
                response = {
                "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {"id": tool_call.id,  
                                     "type": "function",
                                      "function": {
                                        "name": tool_call.function.name,
                                        "arguments": json.dumps(function_args)
                                    }

                                    }
                                ]
                            }
                        }
                    ]
                }
                function_call_result_message = {
                    "role": "tool",
                    "content": sql_response,                    
                    "tool_call_id": tool_call.id
                }

                completion_payload = {
                    "model": st.session_state.gpt4,
                    "messages": [
                        *st.session_state.messages,
                        response['choices'][0]['message'],
                        function_call_result_message
                    ]
                }
                # Second API call: Get the final response from the model
                final_response = client.chat.completions.create(
                    model=st.session_state.gpt4, 
                    messages=completion_payload["messages"],
                )
                msg = final_response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.chat_message("assistant").write(msg)
    else:
        print("No tool calls were made by the model.")  

    
    