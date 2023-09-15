import logging
import azure.functions as func
import os
import json
import openai

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# from dotenv import load_dotenv
# load_dotenv(dotenv_path='../../secrets/aoai.env')

GPT_ENGINE = os.getenv("GPT_ENGINE")

openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getenv("OPENAI_RESOURCE_ENDPOINT")  # SET YOUR RESOURCE ENDPOINT

def get_env_or_hardcoded():
    # Attempt to retrieve the value from the environment
    value = os.getenv("api_version")

    # If the value is not found in the environment, use the default
    if value is None:
        value = "2023-06-01-preview"

    return value

openai.api_version = get_env_or_hardcoded()

admin_key = os.environ.get("AZSEARCH_KEY") # Cognitive Search Admin Key
index_name = os.environ.get("INDEX_NAME") # Cognitive Search index name
credential = AzureKeyCredential(admin_key)

# Create an SDK client
endpoint = os.environ.get("AZSEARCH_EP")

search_client = SearchClient(endpoint=endpoint,
                    index_name=index_name,
                    credential=credential)

def run_openai(prompt, engine=GPT_ENGINE):
    """Recognize entities in text using OpenAI's text classification API."""
    response = openai.ChatCompletion.create(
        engine=engine,

        messages = [
            {"role":"system","content":"You are an AI assistant that helps people find informations."},
            {"role":"user","content": prompt}
        ],
        temperature=.4,
        max_tokens=2048,
    )
    #return response
    return response.choices[0].message.content
    #return response.choices[0].text
    #prompt=prompt,

def azcognitive_score(user_query, topk):
    results = search_client.search(
        search_text=user_query
    )
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
    return f"Answer this question \"{user_query}\" using only the following information  \n <context> {document} </context>"

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="orchestrator")
def orchestrator(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    topk = int(req.params.get('num_search_result'))
    prompt = req.params.get('prompt')

    if prompt is None:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')

    gpt_prompt = azcognitive_score(prompt, topk)
    result = run_openai(gpt_prompt)

    return func.HttpResponse(
        json.dumps({
            "result":result,
        })
    )