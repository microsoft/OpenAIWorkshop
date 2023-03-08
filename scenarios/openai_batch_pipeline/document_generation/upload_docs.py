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
    parser.add_argument('--containername', type=str, help='Azure Storage connection string', default='workshop-data')
    args = parser.parse_args()
    for folder in ["generated_documents", "cleansed_documents"]:
        for filename in os.listdir(folder):
            with open(os.path.join(folder, filename), 'r') as src:
                blob_name=f'{folder}/{filename}'
                blob_client = BlobClient.from_connection_string(
                    args.conn_string,
                    container_name=args.containername,
                    blob_name=blob_name,
                )
                blob_client.upload_blob(src)

if __name__ == '__main__':
    main()