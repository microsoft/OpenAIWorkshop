import os
import openai  
from azure.search.documents.indexes import SearchIndexClient  
from azure.search.documents.models import Vector  #pip install ./build/azure_search_documents-11.4.0b4-py3-none-any.whl  
from azure.search.documents.indexes.models import (  
    SearchIndex,  
    SearchField,  
    SearchFieldDataType,  
    SimpleField,  
    SearchableField,  
    SearchIndex,  
    SemanticConfiguration,  
    PrioritizedFields,  
    SemanticField,  
    SearchField,  
    SemanticSettings,  
    VectorSearch,  
    HnswVectorSearchAlgorithmConfiguration,  
)  
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import requests
from dotenv import load_dotenv
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
credential = AzureKeyCredential(SEARCH_API_KEY)
openai.api_type = "azure"  
openai.api_key = os.getenv("OPENAI_API_KEY")  
openai.api_base = os.getenv("OPENAI_API_BASE")  
openai.api_version = os.getenv("OPENAI_API_VERSION") 

formUrl = os.environ["FILE_URL"]
localFolderPath = os.environ["LOCAL_FOLDER_PATH"]

if (formUrl == "" and localFolderPath == ""):
    print("Please provide a valid FILE_URL or LOCAL_FOLDER_PATH in secrets.env file.")
    exit()



document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)


def create_vector_index(index_name=SEARCH_INDEX):
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT, credential=credential)
    
    try:
        idx = index_client.get_index(index_name)
        return
    except Exception as e:
        if e.status_code == 404:
            pass
        else:
            raise e


    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="text", type=SearchFieldDataType.String,
                        searchable=True, retrievable=True),
        SearchableField(name="summary", type=SearchFieldDataType.String,
                        searchable=True, retrievable=True),                        
        SearchableField(name="fileName", type=SearchFieldDataType.String,
                        searchable=False, retrievable=True),
        SearchableField(name="pageNumber", type=SearchFieldDataType.String,
                        filterable=False, searchable=False, retrievable=True),
        SearchField(name="textVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536, vector_search_configuration="vector-config"),
        SearchField(name="summaryVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536, vector_search_configuration="vector-config"),
    ]

    vector_search = VectorSearch(
      algorithm_configurations=[
          HnswVectorSearchAlgorithmConfiguration(
              name="vector-config",
              kind="hnsw",
              hnsw_parameters={
                  "m": 4,
                  "efConstruction": 400,
                  "efSearch": 500,
                  "metric": "cosine"
              }
          )
      ]
    )

    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=PrioritizedFields(
            title_field=SemanticField(field_name="text"),
            prioritized_keywords_fields=[SemanticField(field_name="summary")]
        )
    )
    # Create the semantic settings with the configuration
    semantic_settings = SemanticSettings(configurations=[semantic_config])

    # Create the search index with the semantic settings
    index = SearchIndex(name=index_name, fields=fields,
                        vector_search=vector_search, semantic_settings=semantic_settings)
    result = index_client.create_index(index)
    return(f' {result.name} created')

def delete_search_index(index_name=SEARCH_INDEX):
    try:
        url = SEARCH_ENDPOINT + "indexes/" + index_name + api_version 
        response  = requests.delete(url, headers=headers)
        return("Index deleted")
    except Exception as e:
        return(e)
    

def add_document_to_index(page_idx, documents, index_name=SEARCH_INDEX):
    try:
        url = SEARCH_ENDPOINT + "indexes/" + index_name + "/docs/index" + api_version
        response  = requests.post(url, headers=headers, json=documents)
        print(f"page_idx is {page_idx} - {len(documents['value'])} Documents added")
    except Exception as e:
        print(e)

def process_afr_result(result, filename):
    print(f"Processing {filename } with {len(result.pages)} pages into Azure Search....this might take a few minutes depending on number of pages...")
    for page_idx in range(len(result.pages)):
        docs = []
        content_chunk = ""
        for line_idx, line in enumerate(result.pages[page_idx].lines):
            #print("...Line # {} has text content '{}'".format(line_idx,line.content.encode("utf-8")))
            content_chunk += str(line.content.encode("utf-8")).replace('b','') + "\n"

            if line_idx != 0 and line_idx % 20 == 0:
              search_doc = {
                    "id":  f"page-number-{page_idx + 1}-line-number-{line_idx}",
                    "text": content_chunk,
                    "textVector": generate_embeddings(content_chunk),
                    "fileName": filename,
                    "pageNumber": str(page_idx+1)
              }
              docs.append(search_doc)
              content_chunk = ""
        search_doc = {
                    "id":  f"page-number-{page_idx + 1}-line-number-{line_idx}",
                    "text": content_chunk,
                    "textVector": generate_embeddings(content_chunk),
                    "fileName": filename,
                    "pageNumber": str(page_idx + 1)
        }
        docs.append(search_doc)   
        add_document_to_index(page_idx, {"value": docs})


# Function to generate embeddings for title and content fields, also used for query embeddings
def generate_embeddings(text):
    response = openai.Embedding.create(
        input=text, engine=os.getenv("OPENAI_MODEL_NAME"))
    embeddings = response['data'][0]['embedding']
    return embeddings



def main():
    create_vector_index()
    if(formUrl != ""):
      print(f"Analyzing form from URL {formUrl}...")
      poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-layout", formUrl)
      result = poller.result()
      print(f"Processing result...this might take a few minutes...")
      process_afr_result(result, "aml-api-v2.pdf")

    if(localFolderPath != ""):
      for filename in os.listdir(localFolderPath):
        file = os.path.join(localFolderPath, filename)    
        with open(file, "rb") as f:
          print(f"Analyzing file {filename} from directory {localFolderPath}...")
          poller = document_analysis_client.begin_analyze_document(
              "prebuilt-layout", document=f
          )
          result = poller.result()
          print(f"{filename}Processing result...this might take a few minutes...")
          process_afr_result(result, filename)
      print(f"done")


if __name__ == "__main__":
    main()