"""
This code sample shows Prebuilt Layout operations with the Azure Form Recognizer client library. 
The async versions of the samples require Python 3.6 or later.

To learn more, please visit the documentation - Quickstart: Form Recognizer Python client library SDKs
https://docs.microsoft.com/en-us/azure/applied-ai-services/form-recognizer/quickstarts/try-v3-python-sdk
"""

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from dotenv import load_dotenv
import os
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

"""
Remember to remove the key from your code when you're done, and never post it publicly. For production, use
secure methods to store and access your credentials. For more information, see 
https://docs.microsoft.com/en-us/azure/cognitive-services/cognitive-services-security?tabs=command-line%2Ccsharp#environment-variables-and-application-configuration
"""
endpoint = os.environ["AFR_ENDPOINT"]
key = os.environ["AFR_API_KEY"]

# sample document
formUrl = "https://anildwablobstorage.blob.core.windows.net/public/azure-machine-learning-2-500.pdf?sv=2021-08-06&st=2023-02-28T03%3A06%3A48Z&se=2024-02-29T03%3A06%3A00Z&sr=b&sp=r&sig=G2mLVs20vil5g1YFoI4ceCEjn8RxzkrCGH8I5AfIxt8%3D"

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
        

try:    
    print(f"Analyze sample azure machine learning document from url: {formUrl}")
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-layout", formUrl)

    print(f"Processing result...this might take a few minutes...")
    result = poller.result()

    delete_search_index()
    create_search_index()

    print(f"Indexing sample document with 500 pages into Azure Search....this might take a few minutes...")
    process_afr_result(result)
    print(f"done")
except Exception as e:
    print(e)


