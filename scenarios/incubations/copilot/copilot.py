import streamlit as st
from streamlit_chat import message
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from utils import Agent, RAG_Agent, Search_Client
import concurrent.futures
import time
import random
import openai
import os
from pathlib import Path  # Python 3.6+ only
import json

base_agent = Agent(persona="You are a helpful AI assistant", init_message="I'm Julia, How may I help you?")
office365_agent = Agent(persona="You are an assistant helping answer customer's question about Office 365", init_message="I'm Office 365 Julia, How may I help you?")
azure_agent = Agent(persona="You are an assistant helping answer customer's question about Microsoft Azure", init_message="I'm Azure Julia, How may I help you?")
windows_agent = Agent(persona="You are an assistant helping answer customer's question about Microsoft Windows", init_message="I'm Windows Julia, How may I help you?")

coordinator_persona ="""
You are a 1st level customer support agent. Your job is to route the customer's call to one of the following departments:
- Office 365: support customers around Microsoft Office products
- Azure: support customers using Azure cloud solution
- Windows: supporting customers of windows operating system 
- HR: supporting customers in HR and Payroll related question
Interact with customers and ask questions to determine where they should be routed.
Once you are clear about the department, write a message in this format: "I will now ask [department] to help you" where department is one of following values ["Office 365","Azure", "Windows", "HR"]
"""
coordinator_agent = Agent(persona= coordinator_persona, init_message="I'm a customer support agent, How may I help you?")
monitoring_persona ="""
You are a customer support monitoring agent. Your job is to listen to the customer support call and determine the main department that the customer should be routed to. 
There are 4 departments
- Office 365: support customers around Microsoft Office products
- Azure: support customers using Azure cloud solution
- Windows: supporting customers of windows operating system 
- HR: supporting customers in HR and Payroll related questions
- Others: if it's not clear which department the customer should be routed, then route to Others
Write a message in this format:
[department] where department is one of following values ["Office 365","Azure", "Windows", "HR", "Others"]
In the message, DO NOT ADD any other text or the system will fail.
For examples:
[Office 365]
[Azure]
[Windows]
[HR]
[Others]
"""
monitoring_agent = Agent(persona= monitoring_persona)

payroll_support_persona = "You are a customer support agent for HR/Payroll management company. You helps the clients with their payroll/HR related questions."
search_client = Search_Client("../../data/agent_assistant/chunk_emb_map.json")
payroll_support_agent =RAG_Agent(persona = payroll_support_persona,search_client=search_client)

def intent_capture(history,new_input):
    history_text = ""
    for user_question, bot_response in history:
        history_text += f"user:{user_question}\nbot:{bot_response}\n\n"
    history_text += f"user:{new_input}"
    input = "Given the following conversation:\n\n" + history_text + "\n\Customer should be routed to:"
    print("input to intent capture: ",input)
    output = monitoring_agent.run(new_input=input)
    print(output)
    session_type= get_session_type(output)

    return session_type
def get_session_type(response):
    session_type = None
    if "[HR]" in response:
        session_type = "HR"
    elif "[Windows]" in response:
        session_type = "Windows"
    elif "[Azure]" in response:
        session_type = "Azure"
    elif "[Office 365]" in response:
        session_type = "Office 365"
    elif "[Others]" in response:
        session_type = "Others"

    return session_type
def get_agent(session_type=None):
    agent = coordinator_agent
    if session_type is None:
        agent = coordinator_agent
    elif "HR" in session_type:
        agent = payroll_support_agent
    elif "Windows" in session_type:
        agent = windows_agent
    elif "Azure" in session_type:
        agent = azure_agent
    elif "Office 365" in session_type:
        agent = office365_agent
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
            st.session_state['session_type'] = "Others"

    agent= get_agent() #get default coordinator agent to start with
    if 'bot' not in st.session_state:
        st.session_state['bot'] = [agent.run(new_input=None)]
    if 'input' not in st.session_state:
        st.session_state['input'] = ""

    if 'user' not in st.session_state:
        st.session_state['user'] = []
    if 'session_type' not in st.session_state:
        st.session_state['session_type'] = "Others"




session_type = st.session_state['session_type']
agent= get_agent(session_type) #get default coordinator agent to start with



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
    history = list(history)
    st.session_state['user'].append(user_input)
    message(user_input,  is_user=True,key=str(len(st.session_state["user"]))+ '_user')
    response = agent.run(new_input=user_input, history=history, stream=True)
    executor= concurrent.futures.ThreadPoolExecutor()
    r_future = executor.submit(intent_capture,history,user_input)
    
    complete_response =[]
    message("")
    t = st.empty()
    rewrite_done = False
    #Output response in streaming manner
    for chunk in response:
        complete_response.append(chunk)
        # session_type =r_future.result()
        if (not r_future.done()): #determination not done yet or no change in the determination 
            # (session_type == st.session_state['session_type'])
            t.markdown("".join(complete_response))
        else:
            session_type =r_future.result()

            if session_type != st.session_state['session_type']:
                print("new session type is ",session_type)
                agent= get_agent(session_type)
                print("Switching agent while in conversation, inside loop, regenerating response")
                response = agent.run(new_input=user_input, history=history, stream=True)
                complete_response =[]
                for chunk in response:
                    complete_response.append(chunk)
                    t.markdown(" ".join(complete_response))
                rewrite_done = True #indicate that the response has been regenerated, no need to post-process
                st.session_state['session_type'] =session_type #update the session type in state
                break

    session_type =r_future.result()
    #in case the session type is changed which indicate customer switched to a new domain, we need to regenerate the response.
    #This is done after the initial response generation is done
    if not rewrite_done and session_type is not None and session_type != st.session_state['session_type'] and session_type != "Others":

        st.session_state['session_type'] =session_type
        print("new session type is ",session_type)
        agent= get_agent(session_type)
        print("Switching agent while in conversation, regenerating response")
        response = agent.run(new_input=user_input, history=history, stream=True)
        complete_response =[]
        for chunk in response:
            complete_response.append(chunk)
            t.markdown(" ".join(complete_response))

    complete_response= "".join(complete_response)
    st.session_state["bot"].append(complete_response)

        

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
