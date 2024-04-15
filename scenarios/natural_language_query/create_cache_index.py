from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    SearchIndex
)

from pathlib import Path  
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
def create_search_index(index_name, searchservice):
    
    index_client = SearchIndexClient(endpoint=f"https://{searchservice}.search.windows.net/",
                                     credential=search_creds)
    if index_name  in index_client.list_index_names():
        print(f"Search index {index_name} already exists, will not recreate it")
        index_client.delete_index(index_name)
    

    fields=[SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="question", type=SearchFieldDataType.String),
            SearchableField(name="code", type=SearchFieldDataType.String),
            SearchableField(name="answer", type=SearchFieldDataType.String),
            SearchField(name="questionVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
            hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
            vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),]

    index = SearchIndex(
        name=index_name,
        fields=fields,


        # Create the semantic settings with the configuration
        semantic_search = SemanticSearch(configurations=[SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=None,
                content_fields=[SemanticField(field_name="question")]
            )
        )]),
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="myHnsw"
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw",
                    )
                ]
                        )
    )
    index_client.create_or_update_index(index)
    print(f"Search index {index_name} created successfully")

if __name__ == "__main__":


    env_path = Path('.') / 'secrets.env'
    load_dotenv(dotenv_path=env_path)

    index = os.getenv("AZURE_SEARCH_INDEX_NAME")
    searchkey = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    openaikey = os.getenv("AZURE_OPENAI_API_KEY")
    openaiservice = os.getenv("AZURE_OPENAI_ENDPOINT")
    searchservice= os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    search_creds = AzureKeyCredential(searchkey)

    client = AzureOpenAI(
    api_key=openaikey,  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint = f"https://{openaiservice}.openai.azure.com"
    )

    create_search_index(index_name=index,  searchservice=searchservice)
