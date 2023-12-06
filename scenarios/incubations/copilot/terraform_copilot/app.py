import os
import sys
import datetime
import streamlit as st
from utils import *

transcript_text=None
with st.sidebar:
    st.title("Whisper Transcription")


    audio_bytes = audio_recorder("click to record", "stop")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        save_audio_file(audio_bytes, "mp3")
    
        # Find the newest audio file
        audio_file_path = max(
            ["files/"+f for f in os.listdir("./files") if f.startswith("audio")],
            key=os.path.getctime,
        )

        # Transcribe the audio file
        transcript_text = transcribe_audio(audio_file_path)

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = chat_deployment

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role":"system", "content":PERSONA},{"role":"assistant", "content":"Hi John, you are currentkly logged-in Azure tenant 0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9 and subscription 840b5c5c-3f4a-459a-94fc-6bad2a969f9d. What can I do for you?"}]

for message in st.session_state.messages:
    # if message.get("role") != "system" and message.get("name") is  None:
    if message.get("role") != "system" and message.get("name") is  None:
        with st.chat_message(message["role"]):
                st.markdown(message["content"])
prompt = st.chat_input("Can you provision a linux VM machine at West US3?")
if transcript_text is not None:
    prompt = transcript_text

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        response= openai.ChatCompletion.create(
            deployment_id=st.session_state["openai_model"],
            messages=st.session_state.messages,
        functions=FUNCTIONS_SPEC,
        function_call="auto", 

        )


        response_message = response["choices"][0]["message"]

        assistant_response =""
            # Step 2: check if GPT wanted to call a function
        if  response_message.get("function_call"):
            print("Recommended Function call:")
            print(response_message.get("function_call"))
            print()
            
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            
            function_name = response_message["function_call"]["name"]
            print("function_name", function_name)
            # verify function has correct number of arguments
            function_args = json.loads(response_message["function_call"]["arguments"])
            
            print("function_args", function_args)
            function_to_call = AVAILABLE_FUNCTIONS[function_name]
            function_response = function_to_call(**function_args)
            print("Output of function call:")
            print(function_response)
            print()

            
            # Step 4: send the info on the function call and function response to GPT
            
            # adding assistant response to messages
            st.session_state.messages.append(
                {
                    "role": response_message["role"],
                    "name": response_message["function_call"]["name"],
                    "content": response_message["function_call"]["arguments"],
                }
            )

            # adding function response to messages
            st.session_state.messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response
        
            assistant_response = openai.ChatCompletion.create(
                messages=st.session_state.messages,
                deployment_id=st.session_state["openai_model"],
                # stream=stream,
            )  # get a new response from GPT where it can see the function response
            assistant_response = assistant_response["choices"][0]["message"]["content"]
        else:
            assistant_response = response_message["content"]
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        st.markdown(assistant_response)
