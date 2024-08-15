import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space

from copilot_utils import PERSONA, AVAILABLE_FUNCTIONS, FUNCTIONS_SPEC, Smart_Agent
import sys
sys.path.append("..")
import os
import json
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
import pandas as pd
# Initialize smart agent with CODER1 persona
agent = Smart_Agent(persona=PERSONA,functions_list=AVAILABLE_FUNCTIONS, functions_spec=FUNCTIONS_SPEC, init_message="Hello, I am your AI  Research Assistant, what can I do for you？")
st.set_page_config(layout="wide",page_title="Smart Research Copilot Demo Application using LLM")
with open("processed_data/frame_to_video_mapping.json", "r") as f:
    frame_mapping = json.load(f)
styl = f"""
<style>
    .stTextInput {{
      position: fixed;
      bottom: 3rem;
    }}
</style>
"""
st.markdown(styl, unsafe_allow_html=True)


MAX_HIST= 3
# Sidebar contents
with st.sidebar:

    st.title('Deep RAG AI Copilot')
    st.markdown('''
    ''')
    st.checkbox("Show AI Assistant's internal thought process", key='show_internal_thoughts', value=False)

    add_vertical_space(5)
    if st.button('Clear Chat'):

        if 'history' in st.session_state:
            st.session_state['history'] = []
        if 'display_data' in st.session_state:
            st.session_state['display_data'] = {}


    st.markdown("""
                
### Sample Questions:  
                


          """)
    st.write('')
    st.write('')
    st.write('')

    st.markdown('####')
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'display_data' not in st.session_state:
        st.session_state['display_data'] = {}
    if 'question_count' not in st.session_state:
        st.session_state['question_count'] = 0
    if 'solution_provided' not in st.session_state:
        st.session_state['solution_provided'] = False

        
user_input= st.chat_input("You:")
## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
display_data = st.session_state['display_data']
question_count=st.session_state['question_count']
# print("new round-----------------------------------")
# print("question_count: ", question_count)

if len(history) > 0:
    #purging history
    removal_indices =[]
    idx=0
    running_question_count=0
    start_counting=False # flag to start including history items in the removal_indices list
    for message in history:
        idx += 1
        message = dict(message)
        print("role: ", message.get("role"), "name: ", message.get("name"))
        if message.get("role") == "user":
            running_question_count +=1
            start_counting=True
        if start_counting and (question_count- running_question_count>= MAX_HIST):
            removal_indices.append(idx-1)
        elif question_count- running_question_count< MAX_HIST:
            break
            
    # remove items with indices in removal_indices
    # print("removal_indices", removal_indices)
    for index in removal_indices:
        del history[index]
    question_count=0
    # print("done purging history, len history now", len(history ))
    for message in history:
        message = dict(message)
        # if message.get("role") != "system":
        #     print("message: ", message)
        # else:
        #     print("system message here, omitted")

        if message.get("role") == "user":
            question_count +=1
            # print("question_count added, it becomes: ", question_count)   
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
    st.session_state['solution_provided'] = False
    st.session_state['feedback'] = False
    with st.chat_message("user"):
        st.markdown(user_input)
        try:
            # stream_out= False
            stream_out, code, history, agent_response,data = agent.run(user_input=user_input, conversation=history, stream=False)
        except Exception as e:
            agent_response= None
            print("error in running agent, error is ", e)
            if 'history' in st.session_state:
                st.session_state['history'] = []
            if 'display_data' in st.session_state:
                st.session_state['display_data'] = {}

    with st.chat_message("assistant"):
        json_response=None
        if agent_response:
            if "overall_explanation"  in agent_response:
                try:
                    agent_response= agent_response.strip("```json")
                    json_response = json.loads(agent_response)
                    st.markdown(json_response.get("overall_explanation")) 
                except Exception as e:
                    print("exception json load ", e)
                    print(agent_response)
                    st.markdown(agent_response)
            if json_response:
                for item in json_response:
                    if item !="overall_explanation":
                        # image_path = os.path.join("videos", item)
                        st.markdown(json_response[item])
                        image_file = item.split("/")[-1]
                        video_file = frame_mapping.get(image_file)["video_file"]
                        video_path = "/".join(item.split("/")[:-1])+"/" + video_file
                        print("video_path ",video_path)
                        
                        print("image_file ", image_file)
                        frame_time = frame_mapping.get(image_file)
                        if frame_time:
                           frame_time = frame_time.get("frame_time")
                        st.image(item)
                        if frame_time:
                            start_time = max(0, frame_time-0.5)
                            end_time = start_time+1
                            if ".MOV" in video_file:
                                video_path= video_path.replace(".MOV", ".mp4")
                                st.video(data=video_path, start_time=start_time, end_time=end_time)
                            else:
                                st.video(data=video_path, start_time=start_time, end_time=end_time)
                        


    if data is not None:
        # print("adding data to session state, data is ", data)
        st.session_state['display_data'] = data

st.session_state['history'] = history
# print("question_count at the end of interaction ", question_count)
st.session_state['question_count'] = question_count
