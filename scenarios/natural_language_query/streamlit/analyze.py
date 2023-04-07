import openai
import string
import ast
import pyodbc
from datetime import timedelta
import os
import pandas as pd
import numpy as np
import random
import imp
import re

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class AnalyzeGPT:
    def __init__(self,tables_structure, system_message,few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password) -> None:
        self.max_response_tokens = max_response_tokens
        self.token_limit= token_limit
        self.gpt_deployment=gpt_deployment
        self.database=database
        self.dbserver=dbserver
        self.db_user = db_user
        self.db_password = db_password
        system_message = f"""
    <<Database structure>>
    {tables_structure}
    {system_message}
    {few_shot_examples}
    """
        self.system_message =  {"role": "system", "content": system_message}

        
    def execute_sql_query(self,query):
        driver="{ODBC Driver 17 for SQL Server}"
        username = self.db_user
        password = self.db_password
        driver = '{ODBC Driver 17 for SQL Server}' # Update the driver version as per your installation  
        
        # Establish the connection  
        conn = pyodbc.connect('DRIVER=' + driver + ';SERVER=' + self.dbserver + ';DATABASE=' + self.database + ';UID=' + username + ';PWD=' + password)  

        
        #logging.info(conn)
        cursor = conn.cursor()
        try:
            cursor.execute(query) 
            data =cursor.fetchall()
        except Exception as e:
            return str(e)

        cols = []
        for i,_ in enumerate(cursor.description):
            cols.append(cursor.description[i][0])
        if len(cols)>0:
            result = pd.DataFrame(np.array(data), columns = cols).head(20) #limit to 20
        else:
            result = pd.DataFrame()

        return result
    def visualize(self,python_code, observation_df,st):
        
        if ('```' in python_code):
            python_code = python_code.split('```')  
            # Extract the content between the first and second delimiter  
            python_code = python_code[1]
            python_code= python_code.strip('python')
        st.code(python_code)  
        N=5
        file_name = ''.join(random.choices(string.ascii_letters, k=N))
        os.makedirs(".tmp", exist_ok=True)
        with open(f".tmp/{file_name}.py", "w") as file:
            file.write(python_code)
        graph = imp.load_source("graph", f".tmp/{file_name}.py")
        fig = graph.visualize_data(observation_df)
        st.plotly_chart(fig)
        os.remove(f".tmp/{file_name}.py")

        

    def run(self, question: str, st) -> any:
        #SQL history contain history of business question and sql query responses from ChatGPT.
        question = {"role":"user", "content":f"Question: {question}"}
        i=1
        history = question
        while True:   
            prompt= [self.system_message] +[history]
            response = openai.ChatCompletion.create(
            engine=self.gpt_deployment, 
            messages = prompt,
            temperature=0,
            max_tokens=self.max_response_tokens,
            stop=f"Observation {i}"
            )
            i+=1
            try:
                llm_output = response['choices'][0]['message']['content']
                print(llm_output)
            except:
                print("error in output ", response)
            output = llm_output.split("\n")
            final_answer_given= False
            for out in output:
                if len(out)>0 and ("Thought" in out or "Observation" in out):
                    st.write(out)
                    if "Answer" in out:
                        st.write(out)
                        final_answer_given= True

            if ("Answer" in llm_output) or (("Query[" not in llm_output) and ("Python[" not in llm_output)):
                if not final_answer_given:
                    st.write(output[-1])
                print("Final answer is given or no actionable action is provided, stop")
                break
            sql_query, python_code ="",""
            try:
                sql_query = re.findall(r"Query\[(.*?)\]", llm_output, re.DOTALL)[0].strip()
                python_code = re.findall(r"Python\[```([\s\S]*?)```]", llm_output)[0]
            except:

                pass
            if len(sql_query)>0 or len(python_code)>0:
                st.write(f"Action {i-1}:")
            if len(sql_query)>0:
                st.code(sql_query)
                
                if ('```' in sql_query):
                    sql_query = sql_query.split('```')  
                    # Extract the content between the first and second delimiter  
                    sql_query = sql_query[1]

                observation = self.execute_sql_query(sql_query)
                st.write(f"Observation {i-1}:")
                display_text =True
                try:
                    observation_out = observation.to_json() #Query execute successfully
                    if len(python_code)>0:
                        self.visualize(python_code,observation,st)
                        display_text=False

                except Exception as e:
                    print(e)
                    observation_out= str(observation)
                if display_text:
                    st.write(observation)
                new_content =  llm_output + f"Observation {i-1}: {observation_out}"
                new_content= history["content"] +"\n"+new_content
                history["content"] = new_content
                







    
