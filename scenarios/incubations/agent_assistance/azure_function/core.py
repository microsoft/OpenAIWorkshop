import numpy as np  
import faiss
import openai
import pandas as pd
import json
import os
import logging
from openai.embeddings_utils import get_embedding
folder_path ="./data"
with open(os.path.join(folder_path, "enriched_emb.json"), "r") as file:
    enriched_emb = json.load(file)
with open(os.path.join(folder_path, "enriched_articles.json"), "r") as file:
    enriched_articles = json.load(file)
with open(os.path.join(folder_path, "topic_content.json"), "r") as file:
    topic_content = json.load(file)

topic_ids =[]
emb_vectors = []
for topic_id, vector in enriched_emb.items():  
    #by default, we use embedding for the entire content of the topic (plus topic descrition).
    # If you you want to use embedding on just topic name and description use this code cosine_sim = cosine_similarity(input_vector, vector[0])
    topic_ids.append(topic_id)
    emb_vectors.append(vector[1])
emb_vectors = np.float32(emb_vectors)
faiss.normalize_L2(emb_vectors)

index = faiss.IndexFlatIP(len(vector[1])) 
index.add(emb_vectors)


API_KEY = "6e78d72911ba4064803b8b14e1f272b8"
RESOURCE_ENDPOINT = "https://azopenaidemo.openai.azure.com/" 

openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
#Note: The openai-python library support for Azure OpenAI is in preview.

user_message = ""
def extract_problems(conversation):
    user_message =f""" 
    Follow this on going conversation below and extract problems that each party may need help with and formulate the search query to the knowledge base search tool.
    <<conversattion>>
    {conversation}
    <<conversattion>>
    Output your response in JSON format {{"problem":"summary of problem", "search_query":"content of search query"}}
    There can be more than 1 problem(s)
    Output just JSON, nothing else.
    Your response:
 
"""
    system_message = """
    You are a senior customer support agent for ADP company. You listen to the conversation between an agent and a customer and assist the agent to resolve the problem.
    You are given access to knowledge base search tool to find knowledge needed to find answer to questions. 

    """
    openai.api_version = "2023-05-15"

    response = openai.ChatCompletion.create(
        timeout=100,
        engine="gpt-35-turbo", # engine = "deployment_name".
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content":user_message },
        ]
    )
    logging.info("response from open ai ", response)
    return response['choices'][0]['message']['content']
            



def find_article_emb_vec(question, topk=3):  
    """  
    Given an input vector and a dictionary of label vectors,  
    returns the label with the highest cosine similarity to the input vector.  
    """  
    openai.api_version = "2022-12-01"

    input_vector = get_embedding(question, engine = 'text-embedding-ada-002')
    input_vector = np.float32([input_vector])
    faiss.normalize_L2(input_vector)
    d,i = index.search(input_vector, k=topk)
    best_topics = [topic_ids[idx] for idx in i[0]]
    logging.info(d)
    output_contents=[topic_content[best_topic] for best_topic in best_topics]
    article_files =[best_topic.split("###")[0] for best_topic in best_topics]
    return article_files, output_contents
question = "Why my paycheck is smaller than usual"

def answer_assist(problem, search_query):

    articles, contents = find_article_emb_vec(search_query,2)
    articles_contents=""
    for article, content in zip(articles, contents):
        articles_contents += f""" 
        article:{article}
        content: {content}
    """
    articles_contents = f"""
    <<knowledge articles>>
    {articles_contents}
    <<knowledge articles>>
    """
    user_message =f""" 
    problem:{problem}
    {articles_contents}
    Your response:
"""
    system_message = """
    You are a senior customer support agent for ADP company. You listen to the conversation between an agent and a customer and assist the agent to resolve the problem.
    Given the question or problem statement and the knowledge article you have, give the answer.
    Rely solely to the guidance from the article.If the knowlege article is not relavant to the question, say you don't know. Do not make up your answer. 
    Cite the name of the knowledge article as source for your answer.
    Format:
    Answer: your answer to the question
    Sources: [source1, source2]
    """
    openai.api_version = "2023-05-15"
    response = openai.ChatCompletion.create(
        engine="gpt-35-turbo", # engine = "deployment_name".
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content":user_message },
        ]
    )
    return response['choices'][0]['message']['content'], articles_contents

# question = "When do I receive my W2 form?"
# answer, articles_contents = answer_assist(question,question)
# print(answer)
# print("---------------content-----------------")

# print(articles_contents)

def recommend_solution(conversation):
    i=0
    result =[]
    while (i<5): #handle wrong format output
        problems=extract_problems(conversation)
        logging.info("problems extracted are "+ str(problems))
        try:
            problems=json.loads(problems)
            for problem in problems:
                answer, articles_contents = answer_assist(problem['problem'],problem['search_query'])
                logging.info(answer)
                logging.info("---------------content-----------------")

                logging.info(articles_contents)
                result.append((problem, answer, articles_contents))
            break

        except Exception as e:
            logging.info(e)
            logging.info("problem parsing json, problems string is ", problems)
            i+=1
    return result

        

