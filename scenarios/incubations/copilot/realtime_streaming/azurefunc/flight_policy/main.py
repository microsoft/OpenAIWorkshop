import logging
from azure.functions import KafkaEvent
import os
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
from azure.search.documents.models import Vector  
import json
import openai
from openai.embeddings_utils import get_embedding, cosine_similarity

service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT") 
index_name = os.getenv("AZURE_SEARCH_POLICY_INDEX") 
index_name = index_name.strip('"')
key = os.getenv("AZURE_SEARCH_ADMIN_KEY") 
key = key.strip('"')
openai.api_key =  os.environ.get("AZURE_OPENAI_API_KEY")
openai.api_base =  os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_type = "azure"
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
emb_engine = emb_engine.strip('"')

credential = AzureKeyCredential(key)
azcs_search_client = SearchClient(service_endpoint, index_name =index_name , credential=credential)
def generate_embeddings(text):
    logging.info("emb_engine: "+ emb_engine)
    logging.info("openai "+ str(os.environ.get("AZURE_OPENAI_API_KEY")))
    openai.api_version = "2023-05-15"
    response = openai.Embedding.create(
        input=text, engine=emb_engine)
    embeddings = response['data'][0]['embedding']
    return embeddings

def search_knowledgebase(search_query):
    vector = Vector(value=generate_embeddings(search_query), k=3, fields="embedding")
    print("search query: ", search_query)
    results = azcs_search_client.search(  
        search_text=search_query,  
        vectors= [vector],
        select=["sourcepage","content"],
        top=5
    )  
    text_content =""
    for result in results:  
        text_content += f"{result['sourcepage']}\n{result['content']}\n"
    print("text_content", text_content)
    return text_content

def add_or_update(new_policy):
    azcs_search_client.merge_or_upload_documents(documents = [new_policy])

def main(kevent : KafkaEvent):
    event_body = kevent.get_body().decode('utf-8')
    logging.info(event_body)
    logging.info(kevent.metadata)
    new_policy = json.loads(json.loads(event_body)['Value'])
    logging.info(new_policy)
    logging.info(new_policy['id'])
    logging.info(new_policy['policy'])
    logging.info(new_policy['airline'])
    logging.info(new_policy['policy_type'])
    contentVector = generate_embeddings(new_policy['policy'])
    new_policy ={"id": new_policy['id'], "policy": new_policy["policy"], "airline":new_policy['airline'], "policy_type": new_policy['policy_type'], "contentVector":contentVector, "active": "true"}
    add_or_update(new_policy)

