import os
import logging
import random
import openai
import time
from azure.storage.blob import BlobClient, BlobServiceClient
import argparse
import json
from azure.core.exceptions import ResourceExistsError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conn_string', type=str, help='Azure Storage connection string')
    parser.add_argument('--containername', type=str, help='Azure Storage connection string', default='workshop-data')
    args = parser.parse_args()
    try:
        blob_service_client = BlobServiceClient.from_connection_string(args.conn_string)
        container_client = blob_service_client.create_container(args.containername)
    except ResourceExistsError:
        print("Container already exists.")
        print("processing...")
    for folder in ["generated_documents", "cleansed_documents"]:
        for filename in os.listdir(folder):
            print("on file:" + filename)
            with open(os.path.join(folder, filename), 'r') as src:
                blob_name=f'{folder}/{filename}'
                print("on blob:" + blob_name)
                blob_client = BlobClient.from_connection_string(args.conn_string,container_name=args.containername,blob_name=blob_name,)
                file_content = src.read()
                blob_client.upload_blob(file_content)

if __name__ == '__main__':
    main()