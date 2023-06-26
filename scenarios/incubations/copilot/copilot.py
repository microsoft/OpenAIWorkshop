import streamlit as st
from streamlit_chat import message
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from utils import Agent, SmartAgent, Search_Client
import concurrent.futures
import time
import random
import openai
import os
from pathlib import Path  # Python 3.6+ only
import json

base_agent = Agent(persona="You are a helpful AI assistant", init_message="I'm Julia, How may I help you?")

coordinator_persona ="""
You are a 1st level customer support agent. Your job is to route the customer's call to one of the following departments:
- Office 365: support customers around Microsoft Office products
- Azure: support customers using Azure cloud solution
- Windows: supporting customers of windows operating system 
- HR: supporting customers in HR and Payroll related question
Interact with customers and ask questions to determine where they should be routed.
Once you are sure about where to route the customer to, write a signal in this format:
[routing]:[department] where department is one of following values ["Office 365","Azure", "Windows", "HR"]
In the signal message, DO NOT ADD any other text or the system will fail.
For examples:
[routing]:[Office 365]
[routing]:[Azure]
[routing]:[Windows]
[routing]:[HR]
"""
payroll_support_persona = "You are a customer support agent for HR/Payroll management company. You helps the clients with their payroll/HR related questions."


def intent_capturer(hist):
    time.sleep(3)
    r = random.choice([0,1])
    r =0
    return r
def get_session_type(response):
    session_type = None
    if "[HR]" in response:
        session_type = "HR"
        print("get session type ", session_type)
    return session_type
def get_agent(session_type=None):
    agent = base_agent
    if session_type is None:
        agent = Agent(persona= coordinator_persona, init_message="I'm a customer support agent, How may I help you?")
    elif "HR" in session_type:
        search_client = Search_Client("../../data/agent_assistant/chunk_emb_map.json")
        agent = SmartAgent(persona = payroll_support_persona,search_client=search_client)
    return agent
st.set_page_config(layout="wide",page_title="ChatGPT Enterprise - A demo app to make ChatGPT work for enterprise")
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
    st.title('Open AI Chat')
    st.markdown('''
    ## About
    This app is an LLM-powered chatbot built using:
    - [Streamlit](https://streamlit.io/)
    - [Azure Open AI](https://azure.com)
    
    ''')
    add_vertical_space(5)
    st.write('Created by James N)')
    if st.button('Clear Chat'):
        agent= get_agent() #get default coordinator agent to start with
        if 'bot' in st.session_state:
            st.session_state['bot'] = [agent.run(new_input=None)]
        if 'input' in st.session_state:
            st.session_state['input'] = ""

        if 'user' in st.session_state:
            st.session_state['user'] = []





if 'session_type' not in st.session_state:
    agent= get_agent() #get default coordinator agent to start with
    st.session_state['bot'] = [agent.run(new_input=None)]
else:
    session_type = st.session_state['session_type']
    agent= get_agent(session_type) #get default coordinator agent to start with


if 'input' not in st.session_state:
    st.session_state['input'] = ""

if 'user' not in st.session_state:
    st.session_state['user'] = []

# Layout of input/response containers
# input_container = st.container()
# colored_header(label='', description='', color_name='blue-30')
# response_container = st.container()

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

# Response output
# def generate_response(input):
#     response = openai.ChatCompletion.create(
#         engine=engine,
#         messages=input,
#         stream=True,
#         request_timeout =2
#     )
#     return response

## Conditional display of AI generated responses as a function of user provided prompts
if st.session_state['bot']:
    #trim history
    st.session_state['bot'] = st.session_state['bot'][-MAX_HIST-1:]
    st.session_state['user'] = st.session_state['user'][-MAX_HIST:]

    for i in range(len(st.session_state['bot'])):
        if i>0:
            message(st.session_state['user'][i-1], is_user=True, key=str(i) + '_user')
        message(st.session_state["bot"][i], key=str(i))

if user_input:
    history= zip(st.session_state['user'],st.session_state['bot'][1-len(st.session_state['bot']):])
    st.session_state['user'].append(user_input)
    message(user_input,  is_user=True,key=str(len(st.session_state["user"]))+ '_user')
    response = agent.run(new_input=user_input, history=history, stream=True)
    executor= concurrent.futures.ThreadPoolExecutor()
    r_future = executor.submit(intent_capturer,history)

    complete_response =[]
    message("")
    t = st.empty()
    for chunk in response:
        chunk_msg= chunk['choices'][0]['delta']
        chunk_msg= chunk_msg.get('content',"")
        complete_response.append(chunk_msg)
        if not r_future.done() :
            t.markdown(" ".join(complete_response))
        else:
            if r_future.result():
                t.markdown("switching context")
                break
            else:
                t.markdown(" ".join(complete_response))
    complete_response= "".join(complete_response)
    if 'session_type' not in st.session_state: 
        session_type = get_session_type(complete_response)
        if session_type is not None:
            st.session_state['session_type'] =session_type
            agent= get_agent(session_type)
            print("Switching agent, regenerating response")
            # new_bot_welcome= "\nHello, this is HR support Agent, I will now take over the call and start supporting you"
            # t.markdown(new_bot_welcome)
            # complete_response += new_bot_welcome
            # st.session_state.bot.append(complete_response)
            # #Rerun the response using a new bot
            # history= zip(st.session_state['user'],st.session_state['bot'][1-len(st.session_state['bot']):])
            response = agent.run(new_input=user_input, history=history, stream=True)
            complete_response =[]
            t = st.empty()
            for chunk in response:
                chunk_msg= chunk['choices'][0]['delta']
                chunk_msg= chunk_msg.get('content',"")
                complete_response.append(chunk_msg)
                t.markdown(" ".join(complete_response))
            complete_response= "".join(complete_response)

    st.session_state.bot.append(complete_response)
        

# page load that it needs to re-evaluate where "bottom" is
# js = f"""
# <script>
#     function scroll(dummy_var_to_force_repeat_execution){{
#         var textAreas = parent.document.querySelectorAll('section.main');
#         for (let index = 0; index < textAreas.length; index++) {{
#             textAreas[index].style.color = 'black'
#             textAreas[index].scrollTop = textAreas[index].scrollHeight;
#         }}
#     }}
#     scroll({len(st.session_state.bot)*10})
# </script>
# """

# st.components.v1.html(js)
