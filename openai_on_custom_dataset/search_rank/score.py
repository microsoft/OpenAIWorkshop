import json
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from sentence_transformers import SentenceTransformer, util
import re 
def search_sentrans(model, query, corpus, top_k=3):
    query_embedding = model.encode(query, convert_to_tensor=True)
    corpus_embedding = model.encode(corpus, convert_to_tensor=True)
    result= util.semantic_search(query_embedding, corpus_embedding, top_k=2,score_function=util.dot_score)
    res=""
    for item in result[0]:
        res = res +" "+ corpus[item['corpus_id']]

    return res
#Defining helper functions
#Splits text after sentences ending in a period. Combines n sentences per chunk.
def splitter(n, s):
    pieces = s.split(". ")
    list_out = [" ".join(pieces[i:i+n]) for i in range(0, len(pieces), n)]
    return list_out

# Perform light data cleaning (removing redudant whitespace and cleaning up punctuation)
def normalize_text(s, sep_token = " \n "):
    s = re.sub(r'\s+',  ' ', s).strip()
    s = re.sub(r". ,","",s)
    # remove all instances of multiple spaces
    s = s.replace("..",".")
    s = s.replace(". .",".")
    s = s.replace("\n", "")
    s = s.strip()
    
    return s
def init():
    global model,search_client
    # Get the path to the deployed model file and load it
    model = SentenceTransformer(os.environ.get("EMB_MODEL"))
    #setting up Azure cognitive service
    admin_key = os.environ.get("AZSEARCH_KEY") # Cognitive Search Admin Key
    index_name = os.environ.get("INDEX_NAME") # Cognitive Search index name
    credential = AzureKeyCredential(admin_key)

    # Create an SDK client
    endpoint = os.environ.get("AZSEARCH_EP")

    search_client = SearchClient(endpoint=endpoint,
                        index_name=index_name,
                        api_version="2021-04-30-Preview",
                        credential=credential)

# Called when a request is received
def run(raw_data):
    try:
        # Get the input data 
        data = json.loads(raw_data)
        user_query=data['prompt']
        # top_k = int(data['topk'])
        # Get a prediction from the model
        results = search_client.search(search_text=user_query, include_total_count=True)
        max_docs = 50
        document=""
        i=0
        while i < max_docs:
            try:
                item = next(results)
                document += (item['completion']+ ": "+ item['context'])
            except:
                break
            i+=1
        document_chunks = splitter(15, normalize_text(document)) #splitting extracted document into chunks of 10 sentences
        context=  search_sentrans(model, user_query, document_chunks, top_k=2)
        return context
    except Exception as e:
        error= str(e)
        return json.dumps(error)