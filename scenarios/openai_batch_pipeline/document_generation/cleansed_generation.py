import os
import logging
import random
import openai
import time
from azure.storage.blob import BlobClient
import argparse
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conn_string', type=str, help='Azure Storage connection string')
    parser.add_argument('--openai_api_base_url', type=str, help='OpenAI API Base URL')
    parser.add_argument('--openai_api_key', type=str, help='OpenAI API Key')
    parser.add_argument('--openai_model', type=str, help='OpenAI Model', default='davincitest')
    args = parser.parse_args()

    temperature= 0.75
    max_tokens= 2000
    top_p= 0.80
    frequency_penalty= 0.25
    presence_penalty= 0.15
    stop= None

    openai.api_type = "azure"
    openai.api_base = args.openai_api_base_url
    openai.api_version = "2022-12-01"
    openai.api_key = args.openai_api_key
    
    for filename in os.listdir('scenarios/openai_batch_pipeline/document_generation/generated_documents'):
        if filename.endswith('.txt'):
            results = {}

            with open(os.path.join("scenarios/openai_batch_pipeline/document_generation/generated_documents", filename), 'r') as src: 
                txt = src.read()

            prmpt = txt + "\n \nProvide summary."

            openai_output = openai.Completion.create(
                engine= args.openai_model,
                prompt= prmpt, 
                temperature= temperature,
                max_tokens= max_tokens,
                top_p= top_p,
                frequency_penalty= frequency_penalty,
                presence_penalty= presence_penalty,
                stop= None)
            results['summary'] = openai_output.choices[0].text
            results["customerSentiment"] = filename.split("_")[3]
            results["topic"] = filename.split("_")[4]
            results["product"] = filename.split("_")[5]
            results["filename"] = filename
            with open(os.path.join("scenarios/openai_batch_pipeline/document_generation/cleansed_documents", filename.split("_")[0]+".json"), 'w') as dest:
                dest.write(json.dumps(results, indent=4))

                file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_documents', filename.split("_")[0]+".json")
                blob_name=f'generated_documents/{filename.split("_")[0]}.json'
                blob_client = BlobClient.from_connection_string(
                    args.conn_string,
                    container_name="workshop-data",
                    blob_name=blob_name,
                )
                blob_client.upload_blob(dest)

if __name__ == '__main__':
    main()