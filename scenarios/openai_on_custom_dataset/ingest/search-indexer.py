"""
This script creates an Azure Search Index and adds documents to it.
The documents are extracted from a PDF using Azure Form Recognizer.
The documents are then indexed using Azure Search.
The index is then used to create a search experience using Azure Cognitive Search.

This is part of Azure OpenAI Workshop
"""

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from dotenv import load_dotenv
import os
import requests
import csv

from pathlib import Path  # Python 3.6+ only
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)


SEARCH_ENDPOINT = os.environ["AZSEARCH_EP"]
SEARCH_API_KEY = os.environ["AZSEARCH_KEY"]
SEARCH_INDEX = os.environ["INDEX_NAME"]
api_version = '?api-version=2021-04-30-Preview'
headers = {'Content-Type': 'application/json',
        'api-key': SEARCH_API_KEY }

endpoint = os.environ["AFR_ENDPOINT"]
key = os.environ["AFR_API_KEY"]

# sample document
formUrl = "https://github.com/microsoft/OpenAIWorkshop/raw/main/scenarios/data/azure-machine-learning-2-500.pdf"

document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)



index_name = "azure-aml-docs"

index_schema = {
  "name": index_name,
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
        url = SEARCH_ENDPOINT + "indexes/" + index_name + api_version 
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



def add_document_to_index(page_idx, documents):
    try:
        url = SEARCH_ENDPOINT + "indexes/" + index_name + "/docs/index" + api_version
        response  = requests.post(url, headers=headers, json=documents)
        print(f"page_idx is {page_idx} - {len(documents['value'])} Documents added")
    except Exception as e:
        print(e)


def process_afr_result(result):
    print(f"Processing sample document with {len(result.pages)} pages into Azure Search....this might take a few minutes...")
    for page_idx in range(len(result.pages)):
        docs = []
        content_chunk = ""
        for line_idx, line in enumerate(result.pages[page_idx].lines):
            #print("...Line # {} has text content '{}'".format(line_idx,line.content.encode("utf-8")))
            content_chunk += str(line.content.encode("utf-8")).replace('b','') + "\n"

            if line_idx != 0 and line_idx % 20 == 0:
              search_doc = {
                    "id":  f"page-number-{page_idx}-line-number-{line_idx}",
                    "text": content_chunk
              }
              docs.append(search_doc)
              content_chunk = ""
        search_doc = {
                    "id":  f"page-number-{page_idx}-line-number-{line_idx}",
                    "text": content_chunk
        }
        docs.append(search_doc)   
        add_document_to_index(page_idx, {"value": docs})
        #create_chunked_data_files(page_idx, search_doc)

def create_chunked_data_files(page_idx, search_doc):
    try:
        output_path = os.path.join(os.getcwd(), "data-files", f'{page_idx}-data.csv')
        with open(output_path, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([search_doc['id'], search_doc['text']])
            
    except Exception as e:
        print(e)
    

try:    
    print(f"Analyze sample azure machine learning document from url: {formUrl}")
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-layout", formUrl)

    print(f"Processing result...this might take a few minutes...")
    result = poller.result()

    delete_search_index()
    create_search_index()    
    process_afr_result(result)
    print(f"done")
except Exception as e:
    print(e)


