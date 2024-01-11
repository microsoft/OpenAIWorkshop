import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from hr_copilot_utils import Smart_Agent,add_to_cache, HR_PERSONA, HR_AVAILABLE_FUNCTIONS, HR_FUNCTIONS_SPEC
import time
import random
import os
from pathlib import Path  
import json
hr_agent = Smart_Agent(persona=HR_PERSONA,functions_list=HR_AVAILABLE_FUNCTIONS, functions_spec=HR_FUNCTIONS_SPEC, init_message="Hi there, this is Lucy, HR specialist helping with answering questions about HR & Payroll and handle personal information updates, may I have your name and employee ID?")

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
    st.title('HR/Payroll Copilot')
    st.markdown('''
    This is a demo of Copilot Concept for HR/Payroll. The Copilot helps employees answer questions and update personal information.

    Copilot will first validate the identity of the employee before answering any questions or updating any information.
    Use ID 1234 or 5678 to test the demo.
   
    Example questions to ask:
    - When will I receive W2 form?
    - Can you explain what are deducted from my paycheck?    
    
    These questions are answered by the Copilot by searching a knowledge base and providing the answer.
                
    Copilot also can help update information. 
    - For address update, the Copilot will update the information in the system. For example: I moved to 123 Main St, San Jose, CA 95112, please update my address
    - For other information update requests, the Copilot will log a ticket to the HR team to update the information, for example: I got married, please update my marital status to married.
    
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


user_input= st.chat_input("You:")

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
      
if len(history) > 0:
    for message in history:
        message = dict(message)
        if message.get("role") != "system" and message.get("role") != "tool" and message.get("name") is None and len(message.get("content")) > 0:
            with st.chat_message(message["role"]):
                    st.markdown(message["content"])
else:
    history, agent_response = hr_agent.run(user_input=None)
    with st.chat_message("assistant"):
        st.markdown(agent_response)
    user_history=[]
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    query_used, history, agent_response = hr_agent.run(user_input=user_input, conversation=history)
    with st.chat_message("assistant"):
        st.markdown(agent_response)

st.session_state['history'] = history