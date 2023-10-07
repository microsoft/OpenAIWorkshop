This is a demo of Multi-Agent Copilot concept. The Copilot helps employees answer questions and update information.
There are 2 agents in the Copilot: inventory forecast and sales forecast. Each agent is responsible for its own domain (sales and inventory).
Depending on the needs of the user, the Copilot will assign the right agent to answer the question.

1. First level support agent help routing the call to the right specialist agent.

2. Sales forecast Copilot help query data and update forecast for sales team. 

    Example questions to ask:

    - What's the forecast for government and product fan at December-01-2022?
    - Can you update the forecast for government and product fan to 3200 at December-01-2022?
    
                
    If questions are not clear, copilot will ask for clarification. For example, if the request to update does not have product, business unit, copilot will ask for clarification. 
                
    Behind the scene, Copilot uses function calling capability to query data and update forecast.
3. Inventory forecast Copilot help query data and update forecast for inventory. It works similar to sales forecast Copilot.


To run this app, go to this folder and run ```streamlit run copilot.py```
Your python environment needs to have all libraries from the requirements.txt file under copilot parent folder


