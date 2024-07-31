import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from multi_agent_utils import *
generic_agent = Smart_Coordinating_Agent(persona=GENERALIST_PERSONA, name="Jenny",functions_spec=GENERAL_FUNCTIONS_SPEC, functions_list= GENERAL_AVAILABLE_FUNCTIONS,init_message="Hi there, this is Jenny, your general support assistant, can I have your name and employee ID?")
it_agent = Smart_Coordinating_Agent(persona=IT_PERSONA,name="Paul", functions_list=IT_AVAILABLE_FUNCTIONS, functions_spec=IT_FUNCTIONS_SPEC)
hr_agent = Smart_Coordinating_Agent(persona=HR_PERSONA,name="Lucy",functions_list=HR_AVAILABLE_FUNCTIONS, functions_spec=HR_FUNCTIONS_SPEC)
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
There are 3 agents in the Copilot: HR, IT and Generalist. Each agent has a different persona and skillset.
Depending on the needs of the user, the Copilot will assign the right agent to answer the question.

1. Generalist copilot help validate the user and answer general questions that are not related to HR and IT.
   - Use ids such as 1234 or 5678 to test the demo. 
   - When the conversation enters any of the HR or IT area, generalist agent will request to transfer to the right specialist agent.

2. For HR Copilot, the agent will answer questions about HR and Payroll and update personal information.

    Example questions to ask:

    - What are deducted from my paycheck?

    These questions are answered by the Copilot by searching a knowledge base and providing the answer.

    Copilot also can help update information.

    - For address update, the Copilot will update the information in the system. For example: I moved to 123 Main St, San Jose, CA 95112, please update my address
    - For other information update requests, the Copilot will log a ticket to the HR team to update the information, for example: I got married, please update my marital status to married.


3. For IT copilot, it helps answer questions about IT. So ask question such as My computer cannot reboot, what should I do?.

                
    ''')
    add_vertical_space(5)
    st.write('Created by James N')
    if st.button('Clear Chat'):
        if 'history' in st.session_state:
            st.session_state['history'] = []
            st.session_state['starting_agent_name']= "Jenny"

    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'starting_agent_name' not in st.session_state:
        st.session_state['starting_agent_name'] = "Jenny"



user_input= st.chat_input("You:")

## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
agent_runner = Agent_Runner(starting_agent_name=st.session_state['starting_agent_name'], agents=[hr_agent, it_agent, generic_agent],  session_state= st.session_state)
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
    stream_out, previous_agent_last_response, history, agent_response = agent_runner.run(user_input=user_input, conversation=history, stream=True)
    with st.chat_message("assistant"):
        if previous_agent_last_response is not None:
            stream_write(st, previous_agent_last_response)
            st.markdown(f"Agent {agent_runner.active_agent.name} is taking over the conversation.")
        if stream_out:
            full_response= stream_write(st, agent_response)
            history.append({"role": "assistant", "content": full_response})
        else:
            st.markdown(agent_response)

st.session_state['history'] = history
st.session_state['starting_agent_name'] = agent_runner.active_agent.name


