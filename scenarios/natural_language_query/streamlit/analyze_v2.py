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
        username = self.db_user
        password = self.db_password
        driver = 'ODBC Driver 17 for SQL Server' # Update the driver version as per your installation  
        
        # Determine the driver for pyodbc that is loaded
        driver_names = [x for x in pyodbc.drivers() if x.endswith(' for SQL Server')]
        if driver_names:
            driver = driver_names[0]
        else:
            print('(No suitable driver found. Cannot connect.)')        

        # Establish the connection  
        conn = pyodbc.connect('DRIVER={' + driver + '};SERVER=' + self.dbserver + ';DATABASE=' + self.database + ';UID=' + username + ';PWD=' + password)  

        
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
        N=5
        exec(python_code, globals())
        fig = visualize_data(observation_df)        
        st.plotly_chart(fig)


        

    def run(self, question: str, st) -> any:
        #SQL history contain history of business question and sql query responses from ChatGPT.
        question = {"role":"user", "content":f"Question: {question}"}
        i=1
        history = question
        while True:   
            prompt= [self.system_message] +[history]
            try:
                response = openai.ChatCompletion.create(
                engine=self.gpt_deployment, 
                messages = prompt,
                temperature=0,
                max_tokens=self.max_response_tokens,
                stop=f"Observation {i}"
                )
                llm_output = response['choices'][0]['message']['content']
            except Exception as e:
                print(e)
                llm_output = "ChatGPT cannot process the message, probably due to large data size"
            i+=1
            
            print("llm_output ",llm_output )
            # pattern = r"```[\s\S]*?```"
            # comment_text = re.sub(pattern, "", llm_output)
            sql_query, python_code ="",""
            # Extract SQL query  
            sql_pattern = r"```SQL\n(.*?)```"  
            sql_query_result = re.findall(sql_pattern, llm_output, re.DOTALL)
            if len(sql_query_result)>0:
                sql_query= sql_query_result[0].strip()
            # Extract Python code  
            python_pattern = r"```Python\n(.*?)```"  
            python_code_result = re.findall(python_pattern, llm_output, re.DOTALL)
            if len(python_code_result)>0:
                python_code= python_code_result[0].strip()
  

            print("SQL Query:\n", sql_query)  
            print("\nPython Code:\n", python_code)  
            comment_text=llm_output.replace(python_code,"")
            comment_text =comment_text.replace(sql_query,"")
            comment_text= comment_text.replace("```Python","")
            comment_text= comment_text.replace("```SQL","")
            comment_text= comment_text.replace("```","")
            comment_text= comment_text.strip()

            # pattern = r".*?(?=(```))"  
            # comment_text = re.findall(pattern, llm_output, re.DOTALL)
            if len(comment_text)>0:
                st.write(comment_text)
                if "Result" in comment_text or "Answer" in comment_text or i>5:
                    print("Result is given or exceed the threshold, finish the loop at ", i)
                    break

            if len(sql_query)>0: #only make sense to continue querying data if there's a SQL
                if len(sql_query)>0:
                    st.code(sql_query)
                if len(python_code)>0:
                    st.code(python_code)        

                observation = self.execute_sql_query(sql_query)
                st.write(f"Observation {i-1}:")
                display_text=True
                try:
                    converted_observation = observation.to_json() #Query execute successfully
                    if len(python_code)>0:
                        self.visualize(python_code,observation,st)
                        display_text=False
                except Exception as e:
                    print(e)
                    converted_observation= str(observation)
                if display_text:
                    st.write(observation)
                new_content =  llm_output + f"Observation {i-1}: {converted_observation}"
                new_content= history["content"] +"\n"+new_content
                history["content"] = new_content
            else:
                print("Final answer is given or no actionable action is provided, stop")
                break
                
                







    