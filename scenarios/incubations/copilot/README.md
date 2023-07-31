# Overview
This solution demonstrates the use of function calling capabily in version 0613 to build your own copilot.
The copilot can interact with users using NL and produce API calls to multiple tools and systems to get information & create updates.

This is a demo of Copilot Concept for HR/Payroll. The Copilot helps employees answer questions and update personal information.

Copilot will first validate the identity of the employee before answering any questions or updating any information. Use ids such as 1234 or 5678 to test the demo.

Example questions to ask:

- When do I receive W2 form?
- What are deducted from my paycheck?
- These questions are answered by the Copilot by searching a knowledge base and providing the answer.

Copilot also can help update information.

- For address update, the Copilot will update the information in the system.
- For other information update requests, the Copilot will log a ticket to the HR team to update the information.

# Installation 
## Open AI setup
Create an Azure OpenAI deployment in an Azure subscription with a GPT-4-0603 deployment .
## Run the application locally
1. Clone the repo (e.g. ```git clone https://github.com/microsoft/OpenAIWorkshop.git``` or download). Then navigate to ```cd scenarios/incubations/copilot```
2. Create a `secrets.env` file in the root of streamlit folder
    AZURE_OPENAI_ENDPOINT="YOUR_OPEN_AI_ENDPOINT"
    AZURE_OPENAI_API_KEY="OPEN_AI_KEY"

3. Create a python environment with version from 3.7 and 3.10
    - [Python 3+](https://www.python.org/downloads/)
        - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
        - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`. 
4. Import the requirements.txt `pip install -r requirements.txt`
5. To run the application from the command line: `streamlit run hr_copilot.py`
## Deploy the application to Azure 
##To be added



