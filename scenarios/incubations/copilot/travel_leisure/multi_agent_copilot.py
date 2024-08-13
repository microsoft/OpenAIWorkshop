import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from multi_agent_utils import Agent_Runner,Smart_Agent, GENERALIST_PERSONA, GENERALIST_FUNCTION_SPEC, GENERALIST_AVAILABLE_FUNCTIONS, FLIGHT_PERSONA, HOTEL_PERSONA, FLIGHT_AVAILABLE_FUNCTIONS, FLIGHT_FUNCTIONS_SPEC, HOTEL_AVAILABLE_FUNCTIONS, HOTEL_FUNCTIONS_SPEC
import json
with open('./data/user_profile.json') as f:
    user_profile = json.load(f)
generalist = Smart_Agent( name="Jenny", persona=GENERALIST_PERSONA.format(customer_name =user_profile['name'], customer_id=user_profile['customer_id']),functions_list=GENERALIST_AVAILABLE_FUNCTIONS, functions_spec=GENERALIST_FUNCTION_SPEC, init_message=f"Hi {user_profile['name']}, this is Jenny,your customer support specialist, what can I do for you?")
flight_specialist = Smart_Agent( name="Maya",persona=FLIGHT_PERSONA.format(customer_name =user_profile['name'], customer_id=user_profile['customer_id']),functions_list=FLIGHT_AVAILABLE_FUNCTIONS, functions_spec=FLIGHT_FUNCTIONS_SPEC, init_message=f"Hi {user_profile['name']}, this is Maya, your flight booking customer specialist, what can I do for you?")
hotel_specialist = Smart_Agent( name="Anna",persona=HOTEL_PERSONA.format(customer_name =user_profile['name'], customer_id=user_profile['customer_id']),functions_list=HOTEL_AVAILABLE_FUNCTIONS, functions_spec=HOTEL_FUNCTIONS_SPEC, init_message=f"Hi {user_profile['name']}, this is Anna, your hotel customer specialist, what can I do for you?")
st.set_page_config(layout="wide",page_title="Real timeCopilot- A demo of Copilot application using GPT on top of real time data")
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
    st.title('Multi-Agent Copilot')
    st.markdown('''
    Multi-Agent Copilot demo.

    ''')
    add_vertical_space(5)
    st.write('Created by James N')
    if st.button('Clear Chat'):

        if 'history' in st.session_state:
            st.session_state['history'] = []
        if "starting_agent_name" in st.session_state:
            st.session_state['starting_agent_name']= "Jenny"


    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'starting_agent_name' not in st.session_state:
        st.session_state['starting_agent_name'] = "Jenny"


user_input= st.chat_input("You:")
agent_runner = Agent_Runner(starting_agent_name=st.session_state['starting_agent_name'], agents=[generalist, hotel_specialist, flight_specialist],  session_state= st.session_state)

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
      
if len(history) > 0:
    for message in history:
        message = dict(message)
        if message.get("role") != "system" and message.get("role") != "tool" and message.get("name") is None and len(message.get("content")) > 0:
            with st.chat_message(message["role"]):
                    st.markdown(message["content"])
else:
    history, agent_response = agent_runner.active_agent.init_history, agent_runner.active_agent.init_history[1]["content"]
    with st.chat_message("assistant"):
        st.markdown(agent_response)
    user_history=[]

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    _, history, agent_response = agent_runner.run(user_input=user_input, conversation=history)
    with st.chat_message("assistant"):
        st.markdown(agent_response)

st.session_state['history'] = history
st.session_state['starting_agent_name'] = agent_runner.active_agent.name
