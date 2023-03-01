import os
import uuid
import openai
from openai.embeddings_utils import get_embedding, cosine_similarity
import re
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import multiprocessing
from dotenv import load_dotenv
from transformers import GPT2TokenizerFast
import requests

from pathlib import Path  # Python 3.6+ only
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)


SEARCH_ENDPOINT = os.environ["AZSEARCH_EP"]
SEARCH_API_KEY = os.environ["AZSEARCH_KEY"]
SEARCH_INDEX = os.environ["INDEX_NAME"]
api_version = '?api-version=2021-04-30-Preview'
headers = {'Content-Type': 'application/json',
        'api-key': SEARCH_API_KEY }

API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # SET YOUR OWN API KEY HERE
RESOURCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # SET A LINK TO YOUR RESOURCE ENDPOINT
CHUNK_SIZE = 10 #int(os.getenv("CHUNK_SIZE"))
#TEXT_SEARCH_EMBEDDING_ENGINE = 'text-search-curie-doc-001'
TEXT_SEARCH_EMBEDDING_ENGINE = 'text-embedding-ada-002'

num_processes = 2 #multiprocessing.cpu_count() - 1




openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
openai.api_version = "2022-06-01-preview"

search_tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
# Create a client
credential = AzureKeyCredential(SEARCH_API_KEY)
search_client = SearchClient(endpoint=SEARCH_ENDPOINT,
                      index_name=SEARCH_INDEX,
                      credential=credential)


index_schema = {
  "name": SEARCH_INDEX,
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "facetable": False,
      "filterable": False,
      "key": True,
      "retrievable": True,
      "searchable": False,
      "sortable": False,
      "indexAnalyzer": None,
      "searchAnalyzer": None,
      "synonymMaps": [],
      "fields": []
    },
    {
      "name": "text",
      "type": "Edm.String",
      "facetable": False,
      "filterable": False,
      "key": False,
      "retrievable": True,
      "searchable": True,
      "sortable": False,
      "indexAnalyzer": None,
      "searchAnalyzer": None,
      "synonymMaps": [],
      "fields": []
    },
    {
      "name": "summary",
      "type": "Edm.String",
      "facetable": False,
      "filterable": False,
      "key": False,
      "retrievable": True,
      "searchable": True,
      "sortable": False,
      "analyzer": "standard.lucene",
      "indexAnalyzer": None,
      "searchAnalyzer": None,
      "synonymMaps": [],
      "fields": []
    },
    {
      "name": "title",
      "type": "Edm.String",
      "facetable": False,
      "filterable": False,
      "key": False,
      "retrievable": True,
      "searchable": True,
      "sortable": False,
      "analyzer": "standard.lucene",
      "indexAnalyzer": None,
      "searchAnalyzer": None,
      "synonymMaps": [],
      "fields": []
    },
    {
      "name": "embedding",
      "type": "Collection(Edm.Double)",
      "facetable": False,
      "filterable": False,
      "retrievable": True,
      "searchable": False,
      "analyzer": None,
      "indexAnalyzer": None,
      "searchAnalyzer": None,
      "synonymMaps": [],
      "fields": []
    }
    
  ],
  "suggesters": [],
  "scoringProfiles": [],
  "defaultScoringProfile": "",
  "corsOptions": None,
  "analyzers": [],
  "semantic": {
     "configurations": [
       {
         "name": "semantic-config",
         "prioritizedFields": {
           "titleField": {
                 "fieldName": "title"
               },
           "prioritizedContentFields": [
             {
               "fieldName": "text"
             }            
           ],
           "prioritizedKeywordsFields": [
             {
               "fieldName": "text"
             }             
           ]
         }
       }
     ]
  },
  "charFilters": [],
  "tokenFilters": [],
  "tokenizers": [],
  "@odata.etag": "\"0x8D8B90E3409E48F\""
}

def delete_search_index():
    try:
        url = SEARCH_ENDPOINT + "indexes/" + SEARCH_INDEX + api_version 
        response  = requests.delete(url, headers=headers)
        print("Index deleted")
    except Exception as e:
        print(e)


def create_search_index():
    try:
        # Create Index
        url = SEARCH_ENDPOINT + "indexes" + api_version
        response  = requests.post(url, headers=headers, json=index_schema)
        index = response.json()
        print("Index created")
    except Exception as e:
        print(e)


def add_document_to_index(documents):
    try:
        url = SEARCH_ENDPOINT + "indexes/" + SEARCH_INDEX + "/docs/index" + api_version
        response  = requests.post(url, headers=headers, json=documents)
        print(f"{len(documents['value'])} Documents added")
    except Exception as e:
        print(e)





def splitter(n, s):
    try:
        pieces = s.split(".")
        list_out = [" ".join(pieces[i:i+n]) for i in range(0, len(pieces), n)]
        return list_out
    except Exception as e:
        print(e)


def normalize_text(s, sep_token = " \n "):
    s = re.sub(r'\s+',  ' ', s).strip()
    s = re.sub(r". ,","",s)
    # remove all instances of multiple spaces
    s = s.replace("..",".")
    s = s.replace(". .",".")
    s = s.replace("\n", "")
    s = s.strip()    
    return s

def test_parallelization(df):
    docs = []
    for index, row in df.iterrows():
        chunks = splitter(CHUNK_SIZE, row['article'])
    
        for chunk in chunks:
            chunk = normalize_text(chunk)

            if(chunk == ""):
                continue
        
            # get embedding for each chunk
            try:
                embedding = get_embedding(chunk, engine = TEXT_SEARCH_EMBEDDING_ENGINE)
            except Exception as e:
                embedding = []
                print(e)
        
            
            #print(f'Error getting embedding for chunk: {chunk}, {e}')
            # add each chunk to search index with embedding
            search_doc = {
                "id":  str(uuid.uuid4()),
                "article": chunk,
                "embedding": embedding,
                "highlights": row['highlights']
            }
            docs.append(search_doc)
            
            #print(json.dumps(docs))
            
            try:
                if(len(docs) > 50):
                    result = search_client.upload_documents(docs)
                    print("Upload of new document succeeded: {}".format(result[0].succeeded))
                    docs = []
            except Exception as e:
                print(e)


def add_search_doc_parallelization(df):
    search_doc_list  = {
                "value": []
            }
    for index, row in df.iterrows():
        text = normalize_text(row["text"])
        # get embedding for each chunk
        try:
            token_len = len(search_tokenizer.encode(text))
            embedding = []
            #response = openai.Embedding.create(
            #    input=text,
            #    model="text-embedding-ada-002"
            #)
            #print(response)
            #embedding = get_embedding(text, engine = TEXT_SEARCH_EMBEDDING_ENGINE)
            
            chunks = splitter(CHUNK_SIZE, text)
            for chunk in chunks:
                search_doc = {
                    "id":  str(uuid.uuid4()),
                    "text":  chunk,
                    "summary": row["summary"],
                    "title": row["title"],
                    "embedding": embedding
                }
                search_doc_list["value"].append(search_doc)  
            
            add_document_to_index(search_doc_list)
            search_doc_list["value"] = []

        except Exception as e:
            embedding = []
            print(e)



def init_processing():
    global df 
    df = pd.read_csv("C:\\source\\repos\\python-files\\search-index\\bill_sum_data.csv")
    chunk_size = int(df.shape[0]/num_processes)
    
    global chunks 
    chunks = [df.iloc[df.index[i:i + chunk_size]] for i in range(0, df.shape[0], chunk_size)]






if __name__ == '__main__':
    init_processing()
    delete_search_index()
    create_search_index()
    pool = multiprocessing.Pool(processes=num_processes)
    result = pool.map(add_search_doc_parallelization, chunks)

print("Done")




