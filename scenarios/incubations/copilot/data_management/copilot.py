import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from functions import *
generic_agent = Smart_Coordinating_Agent(persona=ROUTING_AGENT_PERSONA, name="Jenny",functions_spec=ROUTING_AGENT_FUNCTIONS_SPEC, functions_list= ROUTING_AGENT_FUNCTIONS,init_message="Hi there, this is Jenny, what can I do for you?")
forecast_update_agent = Smart_Coordinating_Agent(persona=SALES_FORECAST_PERSONA,name="Lucy",functions_list=FORECAST_AVAILABLE_FUNCTIONS, functions_spec=SALES_FORECAST_FUNCTIONS_SPEC)
forecast_select_agent = Smart_Coordinating_Agent(persona=INVENTORY_FORECAST_PERSONA,name="Betty",functions_list=FORECAST_AVAILABLE_FUNCTIONS, functions_spec=INVENTORY_FORECAST_FUNCTIONS_SPEC)

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
This is a demo of Multi-Agent Copilot concept. The Copilot helps employees answer questions and update information.
There are 2 agents in the Copilot: inventory forecast and sales forecast. Each agent is responsible for its own domain (sales and inventory).
Depending on the needs of the user, the Copilot will assign the right agent to answer the question.

1. first level support agent help routing the call to the right specialist agent.

2. Sales forecast Copilot help query data and update forecast for sales team. 

    Example questions to ask:

    - What's the forecast for government and product fan at December-01-2022?
    - Can you update the forecast for government and product fan to 3200 at December-01-2022?
    If questions are not clear, copilot will ask for clarification.
    Behind the scene, Copilot uses function calling capability to query data and update forecast.
3. Inventory forecast Copilot help query data and update forecast for inventory. It works similar to sales forecast Copilot.


                
    ''')
    add_vertical_space(5)
    st.write('Created by James N')
    if st.button('Clear Chat'):
        if 'history' in st.session_state:
            st.session_state['history'] = []
            st.session_state['starting_agent_name']= "Jenny"

    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'user_context' not in st.session_state:
        st.session_state['user_context'] = ""
    if 'starting_agent_name' not in st.session_state:
        st.session_state['starting_agent_name'] = "Jenny"



user_input= st.chat_input("You:")

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
agent_runner = Agent_Runner(starting_agent_name=st.session_state['starting_agent_name'], agents=[forecast_update_agent,forecast_select_agent, generic_agent],  session_state= st.session_state)
if len(history) > 0:
    for message in history:
        if message.get("role") != "system" and message.get("name") is  None:
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
    stream_out, request_agent_change, history, agent_response = agent_runner.run(user_input=user_input, conversation=history, stream=True)
    with st.chat_message("assistant"):
        if request_agent_change:
        #     stream_write(st, previous_agent_last_response)
            st.markdown(f"Internal: Agent {agent_runner.active_agent.name} is taking over the conversation.")
        if stream_out:
            full_response= stream_write(st, agent_response)
            history.append({"role": "assistant", "content": full_response})
        else:
            st.markdown(agent_response)

st.session_state['history'] = history
st.session_state['starting_agent_name'] = agent_runner.active_agent.name


