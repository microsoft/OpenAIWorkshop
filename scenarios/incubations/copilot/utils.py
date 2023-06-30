# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import openai
import os
from pathlib import Path  
import json
import re
from dotenv import load_dotenv
import concurrent.futures
from openai.embeddings_utils import get_embedding, cosine_similarity

env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"

class Search_Client():
    def __init__(self,emb_map_file_path):
        with open(emb_map_file_path) as file:
            self.chunks_emb = json.load(file)

    def find_article(self,question, topk=3):  
        openai.api_version = "2022-12-01"
        """  
        Given an input vector and a dictionary of label vectors,  
        returns the label with the highest cosine similarity to the input vector.  
        """  
        input_vector = get_embedding(question, engine = 'text-embedding-ada-002')        
        # Compute cosine similarity between input vector and each label vector
        cosine_list=[]  
        for chunk_id,chunk_content, vector in self.chunks_emb:  
            #by default, we use embedding for the entire content of the topic (plus topic descrition).
            # If you you want to use embedding on just topic name and description use this code cosine_sim = cosine_similarity(input_vector, vector[0])
            cosine_sim = cosine_similarity(input_vector, vector) 
            cosine_list.append((chunk_id,chunk_content,cosine_sim ))
        cosine_list.sort(key=lambda x:x[2],reverse=True)
        cosine_list= cosine_list[:topk]
        best_chunks =[chunk[0] for chunk in cosine_list]
        contents = [chunk[1] for chunk in cosine_list]
        text_content = ""
        for chunk_id, content in zip(best_chunks, contents):
            text_content += f"{chunk_id}\n{content}\n"
        return text_content
def gpt_stream_wrapper(response):
    for chunk in response:
        chunk_msg= chunk['choices'][0]['delta']
        chunk_msg= chunk_msg.get('content',"")
        yield chunk_msg
class Agent(): #Base class for Agent
    def __init__(self, persona, init_message=None, engine= "gpt-35-turbo"):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.init_history =  init_hist
        self.persona = persona
        self.engine = engine
    def generate_response(self, new_input,history=None, stream = False,request_timeout =10):
        openai.api_version = "2023-05-15" 
        if new_input is None: # return init message 
            return self.init_history[1]["content"]
        messages = self.init_history.copy()
        if history is not None:
            for user_question, bot_response in history:
                messages.append({"role":"user", "content":user_question})
                messages.append({"role":"assistant", "content":bot_response})
        messages.append({"role":"user", "content":new_input})
        response = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            stream=stream,
            request_timeout =request_timeout
        )
        if not stream:
            return response['choices'][0]['message']['content']
        else:
            return gpt_stream_wrapper(response)
    def run(self, **kwargs):
        return self.generate_response(**kwargs)

class RAG_Agent(Agent):
    #Agent that can use tools such as search to answer questions.
    answer_prompt_template= """
{persona}. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
Sources:
{sources}
{chat_history}
"""
    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about employee healthcare plans and the employee handbook.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
"""

    def __init__(self, search_client, **kwargs):
        self.search_client = search_client
        super().__init__(**kwargs)
    
    def run(self, new_input,history="", stream = False):
        openai.api_version = "2023-05-15" 

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        chat_history=""
        for user_question, bot_response in history:
            chat_history += f"customer: {user_question}"+"\n"
            chat_history += f"agent: {bot_response}"+"\n"
        prompt = self.query_prompt_template.format(chat_history=chat_history, question=new_input)
        messages = [{"role":"system", "content":"you are a search expert"}, {"role":"user", "content":prompt}]
        completion = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            max_tokens=32, 
            stop=["\n"])
        q = completion['choices'][0]['message']['content']
        sources = self.search_client.find_article(q)
        # print(sources)
        # STEP 2: Generate a contextual and content specific answer using the search results and chat history
        prompt = self.answer_prompt_template.format(persona=self.persona, sources= sources, chat_history=chat_history)
        messages = [{"role":"system", "content":prompt}, {"role":"user", "content":new_input}]
        openai.api_version = "2023-05-15" 

        response = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            stream = stream)
        if not stream:
            return response['choices'][0]['message']['content']
        else:
            return gpt_stream_wrapper(response)



class Smart_Agent(Agent):
    """
    Agent that can use other agents and tools to answer questions.

    Args:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent. Defaults to None.
        engine (str): The name of the GPT engine to use. Defaults to "gpt-35-turbo".

    Methods:
        llm(new_input, stop, history=None, stream=False): Generates a response to the input using the LLM model.
        _run(new_input, stop, history=None, stream=False): Runs the agent and generates a response to the input.
        run(new_input, history=None, stream=False): Runs the agent and generates a response to the input.

    Attributes:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent.
        engine (str): The name of the GPT engine to use.
    """

    def __init__(self, persona,tools, stop, init_message=None, engine= "gpt-35-turbo"):
        super().__init__(persona, init_message, engine)
        #list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        self.tools = tools
        self.stop= stop
    def llm(self, new_input,stop, history=None, stream = False):
        openai.api_version = "2023-05-15" 
        if new_input is None: #if no input return init message
            return self.init_history[1]["content"]
        messages = self.init_history.copy()
        if history is not None:
            for user_question, bot_response in history:
                messages.append({"role":"user", "content":user_question})
                messages.append({"role":"assistant", "content":bot_response})
        messages.append({"role":"user", "content":new_input})
        response = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            stream=stream,
            stop=stop
        )
        if not stream:
            return response['choices'][0]['message']['content']
        else:
            return response
    def _run(self, new_input, stop, history=None, stream = False):
        llm_output = self.llm(new_input, stop, history, stream)
        complete_response = []
        action=[]
        action_string_started = False
        close_bracket_count=0
        if stream:
            for chunk in llm_output:
                chunk_msg= chunk['choices'][0]['delta']
                chunk_msg= chunk_msg.get('content',"")
                if "[" in chunk_msg or action_string_started: #action string starts
                    action_string_started = True
                    action.append(chunk_msg)
                elif "]" in chunk_msg: #action string ends
                    close_bracket_count +=1
                    if close_bracket_count == 3:
                        action_string_started = False
                    action.append(chunk_msg)
                else:
                    complete_response.append(chunk_msg)
                    yield chunk_msg
            action = "".join(action)
        else:
            complete_response = llm_output #non-streaming response
            pattern = r"\[(.*?)\]\[(.*?)\]\[(.*?)\]"  
            
            result = re.search(pattern, complete_response)  
            
            if result:  
                action =result.group()
        action_output = ""
        if type(action) != list:
            pattern = r"\[Message\]\[(.*?)\]\[(.*?)\]"  
    
            result = re.search(pattern, action)
            action_output = None  
            if result:
                tool_name = result.group(1)
                description = result.group(2)
                action_output = self.tools[tool_name].run(new_input=description, stream=stream, request_timeout=10)
            if stream and action_output is not None:
                print("back channel output: ", action_output)
                yield "\n"
                for chunk_msg in action_output:
                    yield chunk_msg
        if not stream:
            yield complete_response+"\n"+action_output
    def run(self, new_input, history=None, stream = False):
        if stream:
            return self._run(new_input, self.stop, history, stream)
        else:
            return list(self._run(new_input, self.stop, history, stream))[0]
