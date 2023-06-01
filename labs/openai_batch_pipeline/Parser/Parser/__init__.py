import logging
import azure.functions as func
import os
import openai
import ast
import json


def main(inputfile: func.InputStream, outputfile: func.Out[str]):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {inputfile.name}\n"
                 f"Blob Size: {inputfile.length} bytes")
    
    endpoint = os.environ.get("OPENAI_RESOURCE_ENDPOINT")
    key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPEAI_MODEL_NAME")

    source = inputfile.read().decode()
    input_name = inputfile.name

    openai.api_type = "azure"
    openai.api_base = endpoint
    openai.api_version = "2022-12-01"
    openai.api_key = key

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

    prompt = source + "\n \nFor the interaction above, provide summary, customer sentiment, and intent in the following JSON format: {'summary':, x, 'customerSentiment': y, 'intent': z}"
    openai_output = openai.Completion.create(
      engine= model,
      prompt= prompt, 
      temperature= temperature,
      max_tokens= max_tokens,
      top_p= top_p,
      frequency_penalty= frequency_penalty,
      presence_penalty= presence_penalty,
      stop= None)
    generated_document = openai_output.choices[0].text

    generated_document = ast.literal_eval(generated_document)
    generated_document['fileName'] = input_name

    outputfile.set(json.dumps(generated_document, indent=4))