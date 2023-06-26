# Agent class
### responsbility definition: expertise, scope, conversation script, style 
import openai
import os
from pathlib import Path  
import json
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
class Agent(): #Base class for Agent
    def __init__(self, persona, init_message=None, engine= "gpt-35-turbo"):
        if init_message is not None:
            init_hist =[{"role":"system", "content":persona}, {"role":"assistant", "content":init_message}]
        else:
            init_hist =[{"role":"system", "content":persona}]

        self.init_history =  init_hist
        self.persona = persona
        self.engine = engine
    def generate_response(self, new_input,history=None, stream = False,request_timeout =5):
        openai.api_version = "2023-05-15" 
        if new_input is None: # return init message 
            return self.init_history[1]["content"]
        messages = self.init_history.copy()
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
        return response
    def run(self, **kwargs):
        return self.generate_response(**kwargs)

class SmartAgent(Agent):
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
        print(sources)
        # STEP 2: Generate a contextual and content specific answer using the search results and chat history
        prompt = self.answer_prompt_template.format(persona=self.persona, sources= sources, chat_history=chat_history)
        print(prompt)
        messages = [{"role":"system", "content":prompt}, {"role":"user", "content":new_input}]
        print(messages)
        openai.api_version = "2023-05-15" 

        response = openai.ChatCompletion.create(
            engine=self.engine,
            messages=messages,
            stream = stream)
        if not stream:
            return response['choices'][0]['message']['content']
        else:
            return response


