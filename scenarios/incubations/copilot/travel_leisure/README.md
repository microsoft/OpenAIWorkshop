### Flight & Hotel Copilot demo application:
#### 1. Environment preperation
- A virtual python environment (between 3.8 and 3.9)
- requirement.txt file

### 2. Standalone copilot scenarios
- Flight booking copilot: 
    - Flight copilot can help customers review current booking, check if there's earlier flight, change flight and answer questions about flight policy etc..
    - To run the application: navigate to travel_leisure and run ```streamlit run flight_copilot.py```
- Hotel booking copilot: 
    - This copilot can help customers review current hotel booking, check if there's earlier availability, change hotel booking and answer questions about hotel policy etc..
    - To run the application: navigate to travel_leisure and run ```streamlit run hotel_copilot.py```

### 3. Multi-copilot copilot scenarios
- Provide a single copilot interface and behind the scence use multiple specialist copilots. This is to enable scaling to multiple scenarios and domain without being too heavy on a copilot
    - To run the application: navigate to travel_leisure and run ```streamlit run multi_agent_copilot.py```



Please create a secrets.env in this folder and provide details about the services. For open AI, please use either GPT-4-1106 or GPT-35-Turbo-1106 for AZURE_OPENAI_CHAT_DEPLOYMENT and GPT-35-Turbo-1106 for for AZURE_OPENAI_EVALUATOR_DEPLOYMENT
```
AZURE_OPENAI_EMB_DEPLOYMENT=
AZURE_OPENAI_EVALUATOR_DEPLOYMENT=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_CHAT_DEPLOYMENT=
AZURE_SEARCH_SERVICE_ENDPOINT=
AZURE_SEARCH_INDEX_NAME=
AZURE_SEARCH_ADMIN_KEY=
```


