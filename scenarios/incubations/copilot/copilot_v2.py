import streamlit as st
from streamlit_chat import message
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from utils import Agent, RAG_Agent, Search_Client, Smart_Agent
import concurrent.futures
import time
import random
import openai
import os
from pathlib import Path  # Python 3.6+ only
import json
#General ChatGPT kind of Agent
base_agent = Agent(persona="You are a helpful AI assistant", init_message="I'm Julia, How may I help you?")

#smart_IT_agent is a kind of agent that can leverage other agents to help answer questions.

smart_IT_agent_persona ="""
You are 1st level support engineer that handle customer's support requests about their laptop computer which includes everything about computer software and hardware.
You have a back channel where you can get support from 2nd level support specialist. The customer should not know about this channel.
Follow this process:
- Engage in generic conversation to identify the issue that the customer have. Your goal is to be able to identify if the issue is about hardware (screen, keyboard...) or operating system or software. If you are not sure, categorize it as Others.
- If it's a software problem, follow these steps:
	- Summarize customer problem and ask for help from a software specialist
	- Sending a message to the specialist by responding in this format [Message][Software][problem description]
	- Get the answer from specialist and respond to customer 
- If it's a hardware problem, follow these steps:
	- Summarize customer problem and ask from a hardware specialist
	- Sending a message to the specialist by responding in this format [Message][Hardware][problem description]
	- Get the answer from specialist and respond to customer
- If it's a Operating System problem, follow these steps:
	- Summarize customer problem and ask for help from an Operating System specialist
	- Sending a message to the specialist by responding in this format [Message][OS][problem description]
	- Get the answer from specialist and respond to customer 
- If it's a Others problem, follow these steps:
	- Summarize customer problem and ask for help from a general specialist
	- Sending a message to the specialist by responding in this format [Message][Others][problem description]
	- Get the answer from specialist and respond to customer 
If the specialist cannot answer, offer customer to log a ticket for engineering research. Gather following inputs from the customer:
- Their preference communication method: email or text then their email or phone number
- How severity level of this issue ["Critical", "medium", "low"]
Then write this message to create a ticket [ticket]["customer name", "customer's communication preference", "customer email/phone", "severity level"]
Make sure everything you have in the ticket was from the customer. Do not make up any information
After the ticket is created succesfully.
- Inform the customer on when they can expert the response from engineering: for critical issue, it's 2 hours, for medium 1 day, for low 2 days.
- Inform customer the ticket number for reference
Remember, customer does not need to know about specifics about communication to back channels. 
Here is an example how you should act:
Customer: Hello there
Support: Hi! How can I help you with your laptop computer today? Please describe the issue you're experiencing.
Customer: It could not boot up
Support: I'm sorry to hear that. When you try to boot up your laptop, do you see any error messages or just a blank screen? And can you hear any sounds, like the fans spinning or any beeps?
Customer: yeah, the screen lit up, windows starting screen appeared but it just stayed there forever
Support: I see. It seems like your laptop is stuck during the boot process. Let me do some research and get back to you. 
Support: [Message][OS][Laptop stuck at Windows starting screen]
Specialist: Here is the solution to the problem
Support: Mr. Customer, here is the solution you may want to try. Let me know how it goes.

Remember, always reach out to specialist to help. Never try to answer technical question directly by yourself.
"""
## Specialist agents as tools for IT specialist agent (Smart Agent)
general_IT_specialist = Agent(persona="You are IT specialist helping answer questions about hardware, software and OS")
os_specialist = Agent(persona="You are IT specialist helping answer questions about OS")
software_specialist = Agent(persona="You are IT specialist helping answer questions about software")
hardware_specialist = Agent(persona="You are IT specialist helping answer questions about hardware")

tools = {"Software": software_specialist, "Hardware": hardware_specialist, "OS": os_specialist, "Others": general_IT_specialist}
smart_IT_agent = Smart_Agent(smart_IT_agent_persona, tools, "Specialist:", "Hello, this is IT support, what can I do for you", "gpt-35-turbo", )

# coordinator_agent is a kind of agent that perform 1st level call routing to the right support function. It is the 1st contact point for customer.

coordinator_persona ="""
You are a 1st level customer support agent. Your job is to route the customer's call to one of the following departments:
- IT: support customers Software, Hardware, and Network related questions
- HR: supporting customers in HR and Payroll related question
- General: Anything else
Interact with customers and ask questions to determine where they should be routed.
Once you are clear about the department, write a message in this format: "I will now ask [department] to help you" where department is one of following values ["Office 365","Azure", "Windows", "HR"]
"""
coordinator_agent = Agent(persona= coordinator_persona, init_message="I'm a customer support agent, How may I help you?")
monitoring_persona ="""
You are a customer support monitoring agent. Your job is to listen to the customer support call and determine the right support function that the customer should be routed to. 
There are 3 support functions
- IT: support customers Software, Hardware, and Network related questions
- HR: supporting customers in HR and Payroll related question
- General: Anything else
Write a message in this format:
[department] where department is one of following values ["IT", "HR", "General"]
In the message, DO NOT ADD any other text or the system will fail.
For examples:
[IT]
[HR]
[General]
"""
# Similiar to coordinator agent, monitoring agent help route the call to the right support function but it does it by monitoring the conversation and may transfer the call mid-conversation.

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
    # print("input to intent capture: ",input)
    output = monitoring_agent.run(new_input=input)
    # print(output)
    session_type= get_session_type(output)

    return session_type
def get_session_type(response):
    session_type = None
    if "[HR]" in response:
        session_type = "HR"
    elif "[IT]" in response:
        session_type = "IT"
    elif "[General]" in response:
        session_type = "General"

    return session_type
def get_agent(session_type=None):
    agent = coordinator_agent
    if session_type is None:
        agent = coordinator_agent
    elif "HR" in session_type:
        agent = payroll_support_agent
    elif "IT" in session_type:
        agent = smart_IT_agent
    elif "General" in session_type:
        agent = base_agent
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
            st.session_state['session_type'] = "General"

    agent= get_agent() #get default coordinator agent to start with
    if 'bot' not in st.session_state:
        st.session_state['bot'] = [agent.run(new_input=None)]
    if 'input' not in st.session_state:
        st.session_state['input'] = ""

    if 'user' not in st.session_state:
        st.session_state['user'] = []
    if 'session_type' not in st.session_state:
        st.session_state['session_type'] = "General"




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
        
        if (not r_future.done()): #determination not done yet or no change in the determination 
            t.markdown("".join(complete_response))
        elif r_future.result()!= st.session_state['session_type']:
            session_type =r_future.result()
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
    if not rewrite_done and session_type != st.session_state['session_type'] and session_type != "General":
        print("new session type is ",session_type)
        st.session_state['session_type'] =session_type
        agent= get_agent(session_type)
        print("Switching agent after regenerating response with original agent, regenerating response")
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