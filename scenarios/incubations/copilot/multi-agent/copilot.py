import streamlit as st
from streamlit_chat import message
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from utils import *
import concurrent.futures
import time
import random
import openai
import os
from pathlib import Path  
import json
generic_agent = Smart_Agent(persona=GENERALIST_PERSONA, name="Jenny",functions_spec=GENERAL_FUNCTIONS_SPEC, functions_list= GENERAL_AVAILABLE_FUNCTIONS, init_message="Hi there, this is Jenny, your general support assistant, how can I help you?")
it_agent = Smart_Agent(persona=IT_PERSONA,name="Paul", functions_list=IT_AVAILABLE_FUNCTIONS, functions_spec=IT_FUNCTIONS_SPEC)
hr_agent = Smart_Agent(persona=HR_PERSONA,name="Lucy",functions_list=HR_AVAILABLE_FUNCTIONS, functions_spec=HR_FUNCTIONS_SPEC, init_message="Hi there, this is Lucy, HR specialist helping with answering questions about HR & Payroll and handle personal information updates, may I have your name and employee ID?")
st.set_page_config(layout="wide",page_title="Enterprise Copilot- A demo of Copilot application using GPT")
styl = f"""
<style>
    .stTextInput {{
      position: fixed;
      bottom: 3rem;
    }}
</style>
"""
st.markdown(styl, unsafe_allow_html=True)


MAX_HIST= 5
# Sidebar contents
with st.sidebar:
    st.title('Copilot')
    st.markdown('''
    This is a demo of Multi-Agent Copilot Concept. The Copilot helps employees answer questions and update information.
    There are 3 agents in the Copilot: HR, IT and Generalist. Each agent has a different persona and skillset.
    Depending on the needs of the user, the Copilot will assign the right agent to answer the question.
    1. For HR Copilot, the agent will answer questions about HR and Payroll and update personal information.

    Copilot will first validate the identity of the employee before answering any questions or updating any information.
    Use ids such as 1234 or 5678 to test the demo.
   
    Example questions to ask:
    - When do I receive W2 form?
    - What are deducted from my paycheck?    
    When do I receive W2 form?When do I receive W2 form?
                
    These questions are answered by the Copilot by searching a knowledge base and providing the answer.
                
    Copilot also can help update information. 
    - For address update, the Copilot will update the information in the system. 
    - For other information update requests, the Copilot will log a ticket to the HR team to update the information.
    2. For IT copilot, it helps answer questions about IT
    3. Generalist copilot helps answer general questions such as company policies, benefits, etc.When do I receive W2 form?
                
    ''')
    add_vertical_space(5)
    st.write('Created by James N')
    if st.button('Clear Chat'):
        if 'history' in st.session_state:
            st.session_state['history'] = []

    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'starting_agent_name' not in st.session_state:
        st.session_state['starting_agent_name'] = "Jenny"




# User input
## Function for taking user provided prompt as input
def clear():
    st.session_state.input_var = st.session_state.input
    st.session_state.input = ''

def get_text():
    st.text_input("You: ", "", key="input", on_change= clear())
    return st.session_state.input_var
## Applying the user input box
# with input_container:
user_input = get_text()

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
agent_runner = Agent_Runner(starting_agent_name=st.session_state['starting_agent_name'], agents=[hr_agent, it_agent, generic_agent])

if len(history) > 0:
    bot_history = [item['content'] for item in history if (item['role'] == 'assistant') and (item.get("name") is  None)]
    #trim history
    # bot_history = bot_history[-MAX_HIST-1:]
    user_history = [item['content'] for item in history if item['role'] == 'user']
    # user_history = user_history[-MAX_HIST-1:]

    for i in range(len(bot_history)):
        if i>0:
            if len(user_history) > i-1:
                message(user_history[i-1], is_user=True, key=str(i) + '_user') #this is because the bot starts first.
        message(bot_history[i], key=str(i))
else:
    history, agent_response = agent_runner.active_agent.init_history, agent_runner.active_agent.init_history[1]["content"]
    message(agent_response, is_user=False, key=str(0) + '_assistant')
    user_history=[]
if user_input:
    message(user_input,  is_user=True,key=str(len(user_history)+1)+ '_user')
    previous_agent_last_response, history, agent_response = agent_runner.run(user_input=user_input, conversation=history)
    agent_response_index = len(bot_history)+1
    if previous_agent_last_response is not None:
            message(previous_agent_last_response,  is_user=False,key=str(agent_response_index)+ '_assistant')
            message(f"Agent {agent_runner.active_agent.name} is taking over the conversation.",  is_user=False,key=str(agent_response_index+1)+ '_assistant')
            agent_response_index +=2
    message(agent_response,  is_user=False,key=str(agent_response_index)+ '_assistant')
st.session_state['history'] = history
st.session_state['starting_agent_name'] = agent_runner.active_agent.name


