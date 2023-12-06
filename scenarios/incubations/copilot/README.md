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

### 3. Build your own copilot

#### Technical design

<img width="1159" alt="image" src="../../../documents/media/hr_copilot_design.png">

Application Platform:

- The solution is built on top of streamlit application platform. Streamlit allows easy creation of  interactive Python application with ability to render rich & responsive UI such as Chat UI and Python data visualization.

Smart Agent:At the heart of the solution is the python object Smart_Agent.  The agent has following components:
- Goals/Tasks: Smart_Agent is given a persona and instructions to follow to achieve certain goals, for example for HR Copilot it is about helping answer HR/Payroll question and update employee's personal information. This is done using instructions specified to the system message.
- NLP interacation & tool execution: For the abilility to use multiple tools and functions to accomplish business tasks, function calling capability of 0613 version is utilized to intelligently select the right function (validate identity/search knowlege base/update address/create ticket) based on the agent's judgement of what need to be done. The agent is also able to engage with users following the instruction/goals defined in the system message.
- Memory: The agent maintain a memomory of the conversation history. The memory is backed by Streamlit's session state.
- LLM: The agent is linked to a 0613 GPT-4 model to power its intelligence.

### 4. Multi-Agent Copilot
<img width="1159" alt="image" src="../../../documents/media/multi-agent_model.png">


When scope for automation spans across multiple functional domains, like human, agent may perform better when it can specialize in a single area.

So instead of stuffing a single agent with multiple capabilities, we can employ multiple agents model, each specializing in a single domain. These agents are managed and coordinated by a manager agent (agent runner).
This is called multi-agent copilot model.

The agent runner is responsible to promote the right agent from the agent pool to be the active agent to interact with user.
It also is responsible to transfer relavant contextfrom agent to agent to ensure continuity.
In this model, the agent runner relies on the specialist agent's cue to back-off from conversation to start the transfer.
Each specialist agent has to implement a skill to send a notification (back-off method) when it thinks its skillset cannot handle the user's request.

On the other hand, the decision on exactly which agent should be selected to take over the conversation is still with agent runner.
When receiving such request, agent runner will revaluate the from the input by the requesting agent to decide on which agent to select for the job. This skill also relies on a LLM. 

Agent runner runs each specialist agent's run method.

There can be some persistent context that should be available across agent's sessions. This is implemented as the persistent memory at agent runner.

Each specialist agent depending on the requirement for skill, can be powered by a gpt-35-turbo or gpt-4.

Multi-agent solution has same application platform (streamlit) as the single HR Copilot. 
# Scenarios
Please go to individual folders to work with one of copilot scenarios



