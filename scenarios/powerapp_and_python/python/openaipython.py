import openai
openai.api_type = "azure"
openai.api_key = "AZURE_OPENAI_API_KEY"
openai.api_base = "AZURE_OPENAI_ENDPOINT"
openai.api_version = "2022-12-01"
openai.api_type = 'azure'

deployment_name='AZURE_OPENAI_MODEL_DEPLOYMENT_NAME'

# create a completion

# Send a completion call to generate an answer
print('Sending a test completion job')
start_phrase = 'Write a tagline for an ice cream shop. '
print('Start Phrase: '+start_phrase)
completion = openai.Completion.create(engine=deployment_name, prompt=start_phrase, max_tokens=10)

# print the completion
print(completion.choices[0].text)

next_phrase = 'Write an email to a colleague named Jill congratulating her on her promotion. The tone should be warm yet professional. Mention how you admire the work she has been putting in.  Include a joke about how her pet lizard Max enjoys eating grasshoppers. Mention how you are looking forward to the team off-site next week.'
print('Next Phrase: '+next_phrase)
completion = openai.Completion.create(engine=deployment_name, prompt=next_phrase, max_tokens=1000)

# print the completion
print(completion.choices[0].text)