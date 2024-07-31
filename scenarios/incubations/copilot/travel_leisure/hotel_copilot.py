import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from hotel_copilot_utils import Smart_Agent, HOTEL_PERSONA, HOTEL_AVAILABLE_FUNCTIONS, HOTEL_FUNCTIONS_SPEC
print(HOTEL_PERSONA)
import json
with open('./data/user_profile.json') as f:
    user_profile = json.load(f)
agent = Smart_Agent(persona=HOTEL_PERSONA.format(customer_name =user_profile['name'], customer_id=user_profile['customer_id']),functions_list=HOTEL_AVAILABLE_FUNCTIONS, functions_spec=HOTEL_FUNCTIONS_SPEC, init_message=f"Hi {user_profile['name']}, this is Anna, your hotel customer specialist, what can I do for you?")

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
    st.title('Hotel booking Copilot')
    st.markdown('''
    Real timeCopilot- A demo of Copilot application using GPT on top of real time data.

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
    history, agent_response = agent.run(user_input=None)
    with st.chat_message("assistant"):
        st.markdown(agent_response)
    user_history=[]
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    query_used, history, agent_response = agent.run(user_input=user_input, conversation=history)
    with st.chat_message("assistant"):
        st.markdown(agent_response)

st.session_state['history'] = history