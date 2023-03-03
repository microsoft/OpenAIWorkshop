import os
import logging
import random
import openai
import time
from azure.storage.blob import BlobClient
import argparse


def randomized_prompt_elements(sentiments_list, topics_list, products_list):
    logging.info('Randomizing prompt elements.')
    # Randomly draw an element from the supplied lists for the sentiment, topic, and product 
    random_sentiment = random.choice(sentiments_list)
    random_topic = random.choice(topics_list)
    random_product = random.choice(products_list)
    
    # Return the randomized element string 
    return random_sentiment, random_topic, random_product

def create_document(doc_generation_engine, document_creation_prompt, temperature=0.7, max_tokens=2000, top_p=1, frequency_penalty=0, presence_penalty=0, stop=None):
    # Takes in the pre-formatted prompt and passes it to the OpenAI model for document generation
    logging.info('Creating randomized document.')

    # Submit the answer from the QA Bot to the AOAI model for summariation
    openai_output = openai.Completion.create(
      engine= doc_generation_engine,
      prompt= document_creation_prompt, 
      temperature= temperature,
      max_tokens= max_tokens,
      top_p= top_p,
      frequency_penalty= frequency_penalty,
      presence_penalty= presence_penalty,
      stop= None)
    
    generated_document = openai_output.choices[0].text

    return openai_output, generated_document

def create_document_name(i, random_sentiment, random_topic, random_product, total_tokens, completion_tokens):
    # Create a name for the document based on the randomly selected sentiment, topic, and product
    logging.info('Creating document name.')
    document_name = f'{i}_{total_tokens}_{completion_tokens}_{random_sentiment}_{random_topic}_{random_product}_document.txt'
    return document_name

def write_generated_documents_as_text(filename, text):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_documents')
    if not os.path.isdir(path):
        os.mkdir(path)
        
    with open(os.path.join(path, filename), 'w') as f:
        f.write(text)

def upload_blob_to_storage(conn_string, filename):
    # Create the client object for the resource identified by the connection
    # string, indicating also the blob container and the name of the specific
    # blob we want.
    file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_documents', filename)
    blob_name=f'generated_documents/{filename}'
    blob_client = BlobClient.from_connection_string(
        conn_string,
        container_name="workshop-data",
        blob_name=blob_name,
    )

    # Open a local file and upload its contents to Blob Storage
    with open(file_name, "rb") as data:
        blob_client.upload_blob(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conn_string', type=str, help='Azure Storage connection string')
    parser.add_argument('--openai_api_base_url', type=str, help='OpenAI API Base URL')
    parser.add_argument('--openai_api_key', type=str, help='OpenAI API Key')
    parser.add_argument('--openai_model', type=str, help='OpenAI Model', default='davincitest')
    args = parser.parse_args()

    # Create access to Azure OpenAI Service and define the api
    openai.api_type = "azure"
    openai.api_base = args.openai_api_base_url
    openai.api_version = "2022-12-01"
    openai.api_key = args.openai_api_key

    # Retrieve the connection string from an environment variable. Note that a
    # connection string grants all permissions to the caller, making it less
    # secure than obtaining a BlobClient object using credentials.
   
    conn_string = args.conn_string
    # Define the OpenAI model to use to generation the document
    doc_generation_engine = args.openai_model

    # Define the model hyperparameters for the document generation
    temperature= 0.75 # Controls randomness: Lowering results in less random completions. \
                        # As the temperature approaches zero, the model will become deterministic and repetitive.
    max_tokens= 2000 # Set a limit on the number of tokens to generate in a response. The system supports a\ 
                        # maximum of 2048 tokens shared between a given prompt and response completion.\
                        #  (One token is roughly 4 characters for typical English text.)
    top_p= 0.80 # Control which tokens the model will consider when generating a response via nucleus sampling.\
                    # Setting this to 0.9 will consider the top 90% most likely of all possible tokens. This \
                    # will avoid using tokens that are clearly incorrect while still maintaining variety\
                    # when the model has low confidence in the highest-scoring tokens.
    frequency_penalty= 0.25 # Reduce the chance of repeating a token proportionally based on how often it has\
                            # appeared in the text so far. This decreases the likelihood of repeating the exact same text in a response.
    presence_penalty= 0.15 # Reduce the chance of repeating any token that has appeared in the text at all so far\
                            # This increases the likelihood of introducing new topics in a response.
    stop= None

    sentiments_list = ['positive', 'negative', 'neutral', 'mixed', 'content', 'upset', 'angry', 'frustrated', 'happy', 'disappointed', 'confused']
    topics_list = ['churn', 'upgrade services', 'downgrade services', 'assistance', 'support', 'information', 'billing', 'payment', 'account', 'service', 'other']
    products_list = ['phone', 'internet', 'tv', 'streaming', 'other']

    for i in range(1000):

        random_sentiment, random_topic, random_product = randomized_prompt_elements(sentiments_list, topics_list, products_list)
        document_creation_prompt = f'You must create a 2,000 word long document representing an exchange between a customer service \
    agent for the fictitious company Contoso Wireless and their customer. The sentiment of the customer must be {random_sentiment} and \
    the topic of the conversation betweem tje agent and customer should center around {random_topic}. The customer must be asking about the product {random_product}. The document should have at least \
    8 back and forth exchanges between the customer and the agent.'

        openai_output, generated_document = create_document(doc_generation_engine, document_creation_prompt, temperature, max_tokens, top_p,\
                                                            frequency_penalty, presence_penalty, stop)

        total_tokens, completion_tokens = openai_output.usage.total_tokens, openai_output.usage.completion_tokens
        document_name = create_document_name(i, random_sentiment, random_topic, random_product, total_tokens, completion_tokens)

        write_generated_documents_as_text(document_name, generated_document)
        upload_blob_to_storage(conn_string, document_name)
        time.sleep(.25)

if __name__ == '__main__': #Provide a summary of this interaction, determine which of the following topics the conversation is about: churn, upgrade services, downgrade services, assistance, support, information, billing, payment, account, service, other, and determine the sentiment of the customer from these choices: positive, negative, neutral, mixed, content, upset, angry, frustrated, happy, disappointed, confused.
    main()