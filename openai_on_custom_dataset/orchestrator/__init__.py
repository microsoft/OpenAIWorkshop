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
GPT_ENGINE = os.getenv("GPT_ENGINE")
PROMPT_URL = os.getenv("PROMPT_URL")
PROMPT_KEY = os.getenv("PROMPT_KEY")
CUSTOM_EMB_URL = os.getenv("CUSTOM_EMB_URL")
CUSTOM_EMB_KEY = os.getenv("CUSTOM_EMB_KEY")

openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
openai.api_base = os.getenv("OPENAI_RESOURCE_ENDPOINT")  # SET YOUR RESOURCE ENDPOINT
openai.api_version = "2022-06-01-preview"

def run_openai(prompt, engine=GPT_ENGINE):
    """Recognize entities in text using OpenAI's text classification API."""
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        temperature=1,
        max_tokens=2048,
    )
    return response.choices[0].text
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
        result = result+" \n "+ prompt
        return result

    except urllib.error.HTTPError as error:
        return("The request failed with status code: " + str(error.code))


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    prompt = req.params.get('prompt')
    search_engine = req.params.get('search_engine')
    dataset = req.params.get('dataset')
    topk = int(req.params.get('num_search_result'))
    print("prompt: ", prompt)
    print("search_engine: ", search_engine)
    print("topk: ", topk)
    if not prompt:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prompt = req_body.get('prompt')
    if search_engine == "custom embedding":
        gpt_prompt = custom_emb_score(prompt, topk)
    else:

        gpt_prompt = tprompt_score(prompt,topk)
    print("gpt_prompt ",gpt_prompt )
    result = run_openai(gpt_prompt)


    return func.HttpResponse(json.dumps({"result":result, "gpt_prompt":gpt_prompt}))
