import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from copilot_utils_v2 import CODER, CODER_AVAILABLE_FUNCTIONS, CODER_FUNCTIONS_SPEC, add_to_cache, Smart_Agent
import sys
sys.path.append("..")
import time
import random
import os
from pathlib import Path  
import json
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
import pandas as pd
# print("AVAILABLE_FUNCTIONS", AVAILABLE_FUNCTIONS)
agent = Smart_Agent(persona=CODER,functions_list=CODER_AVAILABLE_FUNCTIONS, functions_spec=CODER_FUNCTIONS_SPEC, init_message="Hello, I am your data analyst assistant, what can I do for you?")

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
    st.title('Analytic AI Copilot')
    st.markdown('''

    ''')
    add_vertical_space(5)
    st.write('Created by James N, 2024')
    if st.button('Clear Chat'):

        if 'history' in st.session_state:
            st.session_state['history'] = []
        if 'display_data' in st.session_state:
            st.session_state['display_data'] = []

    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'display_data' not in st.session_state:
        st.session_state['display_data'] = []


user_input= st.chat_input("You:")

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
display_data = st.session_state['display_data']
      
if len(history) > 0:
    for message in history:
        message = dict(message)
        if message.get("role") != "system" and message.get("role") != "tool" and message.get("name") is None and len(message.get("content")) > 0:
            with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        elif message.get("role") == "tool":
            data_item = display_data.get(message.get("tool_call_id"), None)
            if  data_item is not None:
                if type(data_item) is PlotlyFigure:
                    st.plotly_chart(data_item)
                elif type(data_item) is MatplotFigure:
                    st.pyplot(data_item)
                elif type(data_item) is pd.DataFrame:
                    st.dataframe(data_item)




else:
    history, agent_response = agent.run(user_input=None)
    with st.chat_message("assistant"):
        st.markdown(agent_response)
    user_history=[]
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    stream_out, query_used, history, agent_response,data = agent.run(user_input=user_input, conversation=history, stream=False)
    with st.chat_message("assistant"):
        if stream_out:
            message_placeholder = st.empty()
            full_response = ""
            for response in agent_response:
                if len(response.choices)>0:
                    full_response += response.choices[0].delta.get("content", "")
                    message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            if query_used: #add to cache
                add_to_cache(query_used, full_response)
                print(f"query {query_used} added to cache")
            history.append({"role": "assistant", "content": full_response})
        else:
            st.markdown(agent_response)
    if data is not None:
        # print("adding data to session state, data is ", data)
        st.session_state['display_data'] = data

st.session_state['history'] = history
