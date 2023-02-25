import logging
import azure.functions as func
import openai
import os
import urllib.request
import json
import os
import ssl
import json
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

GPT_ENGINE = os.getenv("GPT_ENGINE")
PROMPT_URL = os.getenv("PROMPT_URL")
PROMPT_KEY = os.getenv("PROMPT_KEY")
CUSTOM_EMB_URL = os.getenv("CUSTOM_EMB_URL")
CUSTOM_EMB_KEY = os.getenv("CUSTOM_EMB_KEY")

openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getenv("OPENAI_RESOURCE_ENDPOINT")  # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2022-06-01-preview"
admin_key = os.environ.get("AZSEARCH_KEY") # Cognitive Search Admin Key
index_name = os.environ.get("INDEX_NAME") # Cognitive Search index name
credential = AzureKeyCredential(admin_key)

# Create an SDK client
endpoint = os.environ.get("AZSEARCH_EP")

search_client = SearchClient(endpoint=endpoint,
                    index_name=index_name,
                    api_version="2021-04-30-Preview",
                    credential=credential)

def run_openai(prompt, engine=GPT_ENGINE):
    """Recognize entities in text using OpenAI's text classification API."""
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        temperature=1,
        max_tokens=2048,
    )
    return response.choices[0].text
def azcognitive_score(user_query, topk):
    results = search_client.search(search_text=user_query, include_total_count=True, query_type='semantic', query_language='en-us',semantic_configuration_name='maya2')
    document=""
    i=0
    while i < topk:
        try:
            item = next(results)
            document += (item['completion']+ ": "+ item['context'])
        except:
            break
        i+=1
    return f"Answer this question \"{user_query}\" using only the following information  \n <context> {document} </context>"

def tprompt_score(prompt, topk):
    data = {
    "inputs": [prompt],
    "topK": topk,
    }

    url = PROMPT_URL
    # Replace this with the primary/secondary key or AMLToken for the endpoint
    api_key = PROMPT_KEY
    body = str.encode(json.dumps(data))

    # The azureml-model-deployment header will force the request to go to a specific deployment.
    # Remove this header to have the request observe the endpoint traffic rules
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'blue' }

    req = urllib.request.Request(url, body, headers)

    try:
        response = urllib.request.urlopen(req)

        
        result = json.loads(response.read())
        return result['prompts'][0]['context']

    except urllib.error.HTTPError as error:
        return("The request failed with status code: " + str(error.code))

def custom_emb_score(prompt, topk):
    data = {
    "prompt": prompt,
    "topk": topk
    }

    url = CUSTOM_EMB_URL
    # Replace this with the primary/secondary key or AMLToken for the endpoint
    api_key = CUSTOM_EMB_KEY
    body = str.encode(json.dumps(data))

    # The azureml-model-deployment header will force the request to go to a specific deployment.
    # Remove this header to have the request observe the endpoint traffic rules
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'green' }

    req = urllib.request.Request(url, body, headers)

    try:
        response = urllib.request.urlopen(req)

        
        result = json.loads(response.read())
        result = f"Answer this question \"{prompt}\" using only the following information  \n <context> {result} </context>"
        return result

    except urllib.error.HTTPError as error:
        return("The request failed with status code: " + str(error.code))


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    prompt = req.params.get('prompt')
    search_engine = req.params.get('search_engine')
    dataset = req.params.get('dataset')
    topk = int(req.params.get('num_search_result'))
    if not prompt:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')
    if search_engine == "custom embedding":
        gpt_prompt = custom_emb_score(prompt, topk)
    elif search_engine=='azure semantic search':
        gpt_prompt = azcognitive_score(prompt,topk)
    else:

        gpt_prompt = tprompt_score(prompt,topk)
    print("gpt_prompt ",gpt_prompt )
    result = run_openai(gpt_prompt)


    return func.HttpResponse(json.dumps({"result":result, "gpt_prompt":gpt_prompt}))
