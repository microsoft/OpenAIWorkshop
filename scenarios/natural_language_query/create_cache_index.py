from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from pathlib import Path  
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
env_path = Path('.') / 'secrets.env'
load_dotenv(dotenv_path=env_path)
index = os.getenv("AZURE_SEARCH_INDEX_NAME")
searchkey = os.getenv("AZURE_SEARCH_ADMIN_KEY")
openaikey = os.getenv("AZURE_OPENAI_API_KEY")
openaiservice = os.getenv("AZURE_OPENAI_ENDPOINT")
searchservice= os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
def create_search_index():
    print(f"Ensuring search index {index} exists")
    index_client = SearchIndexClient(endpoint=f"https://{searchservice}.search.windows.net/",
                                     credential=search_creds)
    if index not in index_client.list_index_names():
        index = SearchIndex(
            name=index,

            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="question", type=SearchFieldDataType.String),
                SearchableField(name="sql_query", type=SearchFieldDataType.String),
                SearchField(name="questionVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                            hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                            vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
            ],

            # Create the semantic settings with the configuration
            semantic_search = SemanticSearch(configurations=[SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=None,
                    content_fields=[SemanticField(field_name="question")]
                )
            )]),
                vector_search=VectorSearch(
                    algorithms=[
                        HnswAlgorithmConfiguration(
                            name="myHnsw",
                            kind=VectorSearchAlgorithmKind.HNSW,
                            parameters=HnswParameters(
                                m=4,
                                ef_construction=400,
                                ef_search=500,
                                metric=VectorSearchAlgorithmMetric.COSINE
                            )
                        ),
                        ExhaustiveKnnAlgorithmConfiguration(
                            name="myExhaustiveKnn",
                            kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                            parameters=ExhaustiveKnnParameters(
                                metric=VectorSearchAlgorithmMetric.COSINE
                            )
                        )
                    ],
                    profiles=[
                        VectorSearchProfile(
                            name="myHnswProfile",
                            algorithm_configuration_name="myHnsw",
                        ),
                        VectorSearchProfile(
                            name="myExhaustiveKnnProfile",
                            algorithm_configuration_name="myExhaustiveKnn",
                        )
                    ]

                )        
            )
        index_client.create_index(index)
    else:
        print(f"Search index {index} already exists")

if __name__ == "__main__":

    search_creds = AzureKeyCredential(searchkey)


    client = AzureOpenAI(
    api_key=openaikey,  
    api_version="2023-12-01-preview",
    azure_endpoint = f"https://{openaiservice}.openai.azure.com"
    )

    create_search_index()
