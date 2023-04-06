import streamlit as st
import random
import pandas as pd
import sys
sys.path.append('../')
from analyze_v2 import AnalyzeGPT
import openai
import streamlit as st  
st.title('Data Analysis Assistant')
visualization_on = st.checkbox('Enable Visualization', value=False)  

# helper function to parse tables_structure section  
def parse_tables_structure(content):  
    lines = content.split('\n')  
    headers = lines[0].split('\t')  
    table = []  
    for i in range(1, len(lines)):  
        values = lines[i].split('\t')  
        table.append({headers[j]: values[j] for j in range(len(headers))})  
    return table  
  
# helper function to parse faq section  
def parse_faq(content):  
    return content.split('\n')  
  
# helper function to parse system_message section  
def parse_system_message(content):  
    return content.strip()  
  
# helper function to parse visualization_message section  
def parse_visualization_message(content):  
    return content.strip()  
  
# helper function to parse the text file  
import streamlit as st  
  
  
# helper function to parse faq section  
def parse_faq(content):  
    return content.split('\n')  
 
  
# helper function to parse the text file  
def parse_file(content):  
    lines = content.split('\n')  
    result = {}  
    i = 0  
    while i < len(lines):  
        header = lines[i].strip()
        if header == 'tables_structure':
            i+=1
            content = ''  
            while i < len(lines) and not lines[i].startswith('few_shot_examples') and not lines[i].startswith('faq') and not lines[i].startswith('system_message') and not lines[i].startswith('visualization_message'):  
                content += lines[i] + '\n'  
                i += 1  
            result[header] = content 
        elif header == 'faq':
            i+=1
            content = ''  
            while i < len(lines) and not lines[i].startswith('few_shot_examples') and not lines[i].startswith('system_message') and not lines[i].startswith('visualization_message')and not lines[i].startswith('tables_structure'):  
                content += lines[i] + '\n'  
                i += 1  
            result[header] = parse_faq(content.strip())  
        elif header == 'system_message':
            i+=1  
            content = ''  
            while i < len(lines) and not lines[i].startswith('few_shot_examples') and not lines[i].startswith('visualization_message')and not lines[i].startswith('faq')and not lines[i].startswith('tables_structure'):  
                content += lines[i] + '\n'  
                i += 1  
            result[header] = content
        elif header == 'visualization_message': 
            i+=1 
            content = ''  
            while i < len(lines) and not lines[i].startswith('few_shot_examples') and not lines[i].startswith('system_message') and not lines[i].startswith('faq')and not lines[i].startswith('tables_structure'):  
                content += lines[i] + '\n'  
                i += 1  
            result[header] = content 
        elif header == 'few_shot_examples': 
            i+=1 
            content = ''  
            while i < len(lines) and not lines[i].startswith('visualization_message') and not lines[i].startswith('system_message') and not lines[i].startswith('faq')and not lines[i].startswith('tables_structure'):  
                content += lines[i] + '\n'  
                i += 1  
            result[header] = content 

        else:  
            i += 1  
    return result    
# streamlit app code  
faq, tables_structure, visualization_message,system_message,few_shot_examples="","","","",""
# file upload  
uploaded_file = st.file_uploader(label="Config file",help ="Upload config file")  
if uploaded_file is not None:  
    content = uploaded_file.read().decode('utf-8')  
    try:  
        result = parse_file(content) 
        # validate content  
        if 'system_message' not in result or 'tables_structure' not in result:  
            st.error("Invalid file content, system_message and tables_structure must be present")  
        else:  
            tables_structure = result["tables_structure"] 
            system_message = result["system_message"] 
            visualization_message= result.get("visualization_message","")
            faq = result.get("faq","")
    except:  
        st.error("File format invalid")  
if visualization_on:
    system_message+= visualization_message

openai.api_type = "azure"
openai.api_key = ""  # SET YOUR OWN API KEY HERE
openai.api_base = "" # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview" 
max_response_tokens = 1250
token_limit= 4096
gpt_deployment="chatgpt"
gpt_deployment="gpt-35-turbo"
database=""
dbserver=""
db_user=""
db_password= ""
analyzer = AnalyzeGPT(tables_structure, system_message, few_shot_examples, gpt_deployment,max_response_tokens,token_limit,database,dbserver,db_user, db_password)


option = st.selectbox('FAQs',faq)



question = st.text_area("Ask me a  question on churn", option)
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    
    analyzer.run(question, st)