import asyncio  
import uvicorn  
from fastapi import FastAPI, Request  
from pydantic import BaseModel  
import pickle  
  
from agent import Agent  # Your existing agent class  
  
# In-memory session store (use Redis/DB for production)  
SESSION_STORE = {}  
  
app = FastAPI()  
  
class ChatRequest(BaseModel):  
    session_id: str  
    prompt: str  
  
class ChatResponse(BaseModel):  
    response: str  
  
@app.post("/chat", response_model=ChatResponse)  
async def chat(req: ChatRequest):  
    # Lookup or create agent for this session  
    if req.session_id in SESSION_STORE:  
        agent_state = SESSION_STORE[req.session_id]  
    else:  
        agent_state = None  
  
    agent = Agent(state=agent_state)  
    # Run chat  
    answer = await agent.chat_async(req.prompt)  
  
    # Update/store latest agent state  
    if agent.loop_agent:  
        new_state = await agent.loop_agent.save_state()  
        SESSION_STORE[req.session_id] = new_state  
  
    return ChatResponse(response=answer)  
  
if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)  