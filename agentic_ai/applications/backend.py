import asyncio
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
import pickle
import os
from typing import List, Dict
from dotenv import load_dotenv
import importlib
import sys
from pathlib import Path

# Load environment variables from .env file.
load_dotenv()

# Add parent directory (contoso_internet) to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
agent_module_path = os.getenv("AGENT_MODULE")
agent_module = importlib.import_module(agent_module_path)
Agent = getattr(agent_module, "Agent")


# In-memory session store (use Redis/DB for production)
SESSION_STORE = {}

app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    prompt: str


class ChatResponse(BaseModel):
    response: str


class ConversationHistoryResponse(BaseModel):
    session_id: str
    history: List[Dict[str, str]]


class SessionResetRequest(BaseModel):
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Lookup or create agent for this session
    agent = Agent(SESSION_STORE, req.session_id)
    # Run chat
    answer = await agent.chat_async(req.prompt)

    return ChatResponse(response=answer)


@app.post("/reset_session")
async def reset_session(req: SessionResetRequest):
    # Reset the session by removing the chat history from SESSION_STORE
    if req.session_id in SESSION_STORE:
        del SESSION_STORE[req.session_id]
    if f"{req.session_id}_chat_history" in SESSION_STORE:
        del SESSION_STORE[f"{req.session_id}_chat_history"]


@app.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str):
    # Retrieve chat history list from SESSION_STORE using the correct key
    history = SESSION_STORE.get(f"{session_id}_chat_history", [])
    return ConversationHistoryResponse(session_id=session_id, history=history)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000)
