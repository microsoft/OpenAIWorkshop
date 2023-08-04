# Scenario Overview

<img width="1159" alt="image" src="../../../documents/media/copilot_concept.png">


# Developing Copilot Solution

### 1. Copilot Solution Model

In a copilot solution, the natural language input (prompt) can result in a output of API call syntax or code that can be executed against an API, a tool or an application platform that perform an intended business transaction.

On top of this, copilot can perform multiple interactions with user or with other systems to achieve certain goal. For example, a shopping copilot may interact with the user to help them make a purchase decision by recommending products then execute order creation at the end.

<img width="1159" alt="image" src="../../../documents/media/copilot_model.png">

### 2. Understand function calling capability in GPT

Developers can now describe functions to gpt-4-0613 and gpt-3.5-turbo-0613, and have the model intelligently choose to output a JSON object containing arguments to call those functions. This is a new way to more reliably connect GPT's capabilities with external tools and APIs.
These models have been fine-tuned to both detect when a function needs to be called (depending on the user’s input) and to respond with JSON that adheres to the function signature. Function calling allows developers to more reliably get structured data back from the model. 

Follow this example to understand how function calling works

https://github.com/Azure-Samples/openai/blob/main/Basic_Samples/Functions/working_with_functions.ipynb

### 3. Build your own HR/Payroll copilot
Having understood how function calling works, it's time to build an end to end HR/Payroll copilot solution. 

####  Functional Flow
This is a demo of Copilot Concept for HR/Payroll. The Copilot helps employees answer questions and update personal information.

Copilot will first validate the identity of the employee before answering any questions or updating any information. Use ids such as 1234 or 5678 to test the demo.

Example questions to ask:

- When do I receive W2 form?
- What are deducted from my paycheck?
- These questions are answered by the Copilot by searching a knowledge base and providing the answer.

Copilot also can help update information.

- For address update, the Copilot will update the information in the system.
- For other information update requests, the Copilot will log a ticket to the HR team to update the information.

#### Technical design

<img width="1159" alt="image" src="../../../documents/media/hr_copilot_design.png">

Application Platform:

- The solution is built on top of streamlit application platform. Streamlit allows easy creation of  interactive Python application with ability to render rich & responsive UI such as Chat UI and Python data visualization.

Smart Agent:At the heart of the solution is the python object Smart_Agent.  The agent has following components:
- Goals/Tasks: Smart_Agent is given a persona and instructions to follow to achieve the goals of helping answer HR/Payroll question and update employee's personal information. This is done using instructions specified to the system message.
- NLP interacation & tool execution: For the abilility to use multiple tools and functions to accomplish business tasks, function calling capability of 0613 version is utilized to intelligently select the right function (validate identity/search knowlege base/update address/create ticket) based on the agent's judgement of what need to be done. The agent is also able to engage with users following the instruction/goals defined in the system message.
- Memory: The agent maintain a memomory of the conversation history. The memory is backed by Streamlit's session state.
- LLM: The agent is linked to a 0613 GPT-4 model to power its intelligence.

### 4. Multi-Agent Copilot
<img width="1159" alt="image" src="../../../documents/media/multi-agent_model.png">

When the scope for automation span across multiple functional domains, just like human, agent may perform better when it specializes in a single area.
In terms of implementation, a specialized agent's instruction and prompt can be limited into a narrow domain so it may perform more reliably.
On the other hand, there needs to be a coordination mechanism to move the session across participating agents smoothly and to enable hand-over of information from one agent to next. In addition, each participating agent needs to be intructed as how to hand over when it's supposed to.

#### Function flow

This is a demo of Multi-Agent Copilot concept. The Copilot helps employees answer questions and update information.
There are 3 agents in the Copilot: HR, IT and Generalist. Each agent has a different persona and skillset.
Depending on the needs of the user, the Copilot will assign the right agent to answer the question.
1. For HR Copilot, the agent will answer questions about HR and Payroll and update personal information.

Copilot will first validate the identity of the employee before answering any questions or updating any information.
Use ids such as 1234 or 5678 to test the demo.

Example questions to ask:
- When do I receive W2 form?
- What are deducted from my paycheck?    
When do I receive W2 form?When do I receive W2 form?
            
These questions are answered by the Copilot by searching a knowledge base and providing the answer.
            
Copilot also can help update information. 
- For address update, the Copilot will update the information in the system. 
- For other information update requests, the Copilot will log a ticket to the HR team to update the information.
2. For IT copilot, it helps answer questions about IT
3. Generalist copilot helps answer general questions such as company policies, benefits, etc.When do I receive W2 form?


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
5. To run the HR/Payroll copilot from the command line: `streamlit run hr_copilot.py`
5. To run the multi-agent copilot, ```cd multi-agent``` then `streamlit run /copilot.py`

## Deploy the application to Azure 
##To be added







