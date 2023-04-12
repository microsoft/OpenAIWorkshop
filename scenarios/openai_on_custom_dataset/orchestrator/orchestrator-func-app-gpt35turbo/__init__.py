import logging
import azure.functions as func
import os
import urllib.request
import json
import os
import ssl
import json
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import openai


GPT_ENGINE = os.getenv("GPT_ENGINE_35")

openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getenv("OPENAI_RESOURCE_ENDPOINT")  # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2023-03-15-preview"
admin_key = os.environ.get("AZSEARCH_KEY") # Cognitive Search Admin Key
index_name = os.environ.get("INDEX_NAME") # Cognitive Search index name
credential = AzureKeyCredential(admin_key)

# Create an SDK client
endpoint = os.environ.get("AZSEARCH_EP")

semantic_config = os.environ.get("SEMANTIC_CONFIG")

search_client = SearchClient(endpoint=endpoint,
                    index_name=index_name,
                    api_version="2021-04-30-Preview",
                    credential=credential)

def run_openai(prompt, engine=GPT_ENGINE):
    """Recognize entities in text using OpenAI's text classification API."""
    max_response_tokens = 1250
    token_limit= 4096   
    try:
        response = openai.ChatCompletion.create(
                    engine=GPT_ENGINE, 
                    messages = prompt,
                    temperature=0,
                    max_tokens=max_response_tokens,
                    stop=f"Answer:"
                    )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return e.user_message


def azcognitive_score(user_query, topk):
    results = search_client.search(search_text=user_query, include_total_count=True, query_type='semantic', query_language='en-us',semantic_configuration_name=semantic_config)
    document=""
    i=0
    while i < topk:
        try:
            item = next(results)
            document += (item['text'])
        except Exception as e:
            print(e)
            break
        i+=1
    system_message="""
    You are an AI search Assitant. You are given a question and a context. You need to answer the question using only the context.
    If you do not know the Answer, you can say "I don't know".  
    The context is a collection of documents.    
    """
    system_message =  {"role": "system", "content": system_message}
    question = {"role":"user", "content":f"Question: {user_query} \n <context> {document} </context>"}
    prompt= [system_message] +[question]
    return prompt


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    prompt = req.params.get('prompt')
    #search_engine = req.params.get('search_engine')
    #dataset = req.params.get('dataset')
    topk = int(req.params.get('num_search_result'))
    if prompt is None:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')
    gpt_prompt = None

    try:
        gpt_prompt = azcognitive_score(prompt,topk)
    except Exception as e:
        return func.HttpResponse(json.dumps(e))

    print("gpt_prompt ",gpt_prompt )

    #result = None
    #try:
    result = run_openai(gpt_prompt)
    return func.HttpResponse(json.dumps({"result":result, "gpt_prompt":gpt_prompt}))
    #except Exception as e:
    #    return func.HttpResponse(json.dumps(e))

    