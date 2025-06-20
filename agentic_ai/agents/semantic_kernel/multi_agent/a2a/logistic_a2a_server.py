"""  
Contoso – Logistics A2A façade  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  
Bridges the internal Fast-MCP logistics tools into the Google A2A  
protocol.  All business logic continues to live in the MCP service; this  
wrapper merely acts as a protocol translator.  
  
• Listens on  http://0.0.0.0:9100/  
• Exposes one skill:  return-pick-up scheduling  
• Streams a single final message per request  
"""  
from __future__ import annotations  
  
import asyncio  
import json  
import logging  
import os  
from typing import Any  
  
import uvicorn  

from a2a.server.agent_execution import AgentExecutor,RequestContext
from a2a.server.apps import A2AStarletteApplication  
from a2a.server.request_handlers import DefaultRequestHandler  
from a2a.server.tasks import InMemoryTaskStore  
from a2a.server.events import EventQueue
from a2a.types import (  
    AgentCapabilities,  
    AgentCard,  
    AgentSkill,  
    Message,  
)  
from a2a.utils import new_agent_text_message, new_task
from semantic_kernel.agents import ChatCompletionAgent  
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion  
from semantic_kernel.connectors.mcp import MCPSsePlugin  
from typing import Any, Dict, List, Optional  

from dotenv import load_dotenv  
# ────────────────────────  Load environment variables  ───────────
load_dotenv()

# ─────────────────────────  Logging  ──────────────────────────  
logging.basicConfig(level=logging.INFO)  
log = logging.getLogger("logistics-a2a")  

# ────────────────────────  Agent State Store  ────────────────────────────
AGENT_STATE_STORE: Dict[str, Any] = {}
  
# ─────────────────────────  Environment  ──────────────────────  
MCP_URI = os.getenv("LOGISTIC_MCP_SERVER_URI", "http://localhost:8100/sse")  
AZ_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
  
# ───────────────────────  Build SK Logistics agent  ───────────  
async def build_sk_logistics_agent() -> ChatCompletionAgent:  
    """  
    Creates the Semantic-Kernel ChatCompletionAgent and opens the SSE  
    connection to the Fast-MCP server.  
    """  
    logistic_plugin = MCPSsePlugin(  
        name="LogisticMCP",  
        description="Logistics MCP plugin",  
        url=MCP_URI,  
        headers={"Content-Type": "application/json"},  
        timeout=30,  
    )  
    await logistic_plugin.connect()  
  
    instructions = (  
        "You are the Logistics AI agent responsible for arranging product-return "  
        "pick-ups."  
        "Supported request types:\n"  
        "  • availability_request: requireing pickup address and preferred data range\n"  
        "  • schedule_pickup: need order_id, address and timeslot\n"  
        "  • cancel_request\n." \

    )  
  
    agent = ChatCompletionAgent(  
        name="logistics_sk_agent",  
        service=AzureChatCompletion(deployment_name=AZ_DEPLOYMENT),  
        instructions=instructions,  
        plugins=[logistic_plugin],  
    )  
    return agent  
  
  
# ────────────────────────  Agent Executor  ─────────────────────  
class LogisticsA2AExecutor(AgentExecutor):  
    """  
    Thin wrapper that forwards the raw JSON payload to a Semantic-Kernel  
    agent which, in turn, calls the Logistics MCP tools.  
  
    The SK agent is created lazily on first use so we do not need an  
    event-loop during __init__.  
    """  
  
    def __init__(self) -> None:  
        self._agent: ChatCompletionAgent | None = None  
        self._agent_lock = asyncio.Lock()  # guards one-time initialisation  
  
    async def _get_agent(self) -> ChatCompletionAgent:  
        if self._agent is None:  
            async with self._agent_lock:  
                if self._agent is None:  # double-checked  
                    self._agent = await build_sk_logistics_agent()  
        return self._agent  
  
    async def execute(      # type: ignore[override]  
        self,  
        context: RequestContext,  
        event_queue: EventQueue,  
    ) -> None:  
        try:  
            agent = await self._get_agent()  
            query = context.get_user_input()
            print(f"Received query: {query}")
            task = context.current_task
            if not task:
                task = new_task(context.message)
                await event_queue.enqueue_event(task)
            #get thread from session store
            thread = AGENT_STATE_STORE.get(task.contextId, {})
            # Retrieve user's raw JSON payload (1st text part)  
  
            # Forward request to the SK logistics agent  
            if thread:
                response = await agent.get_response(messages=query, thread=thread) 
            else:
                response = await agent.get_response(messages=query)
            response_content = str(response.content) 
            print(f"Response content: {response_content}")
            # Update the thread in the session store
            AGENT_STATE_STORE[task.contextId] = response.thread if response.thread else {}
  
            # Ensure the answer is valid JSON  
  
            await event_queue.enqueue_event(  
                new_agent_text_message(response_content,  task.contextId,
                            task.id) 
            )  
  
        except Exception as exc:  # pragma: no cover  
            logging.exception("LogisticsA2AExecutor error")  
            event_queue.enqueue_event(  
                new_agent_text_message(f"ERROR: {exc}")  
            )  
  
    async def cancel(       # type: ignore[override]  
        self,  
        context: RequestContext,  
        event_queue: EventQueue,  
    ) -> None:  
        event_queue.enqueue_event(  
            new_agent_text_message("Cancellation not supported", is_final=True)  
        )  
  
  
# ──────────────────────────  Agent Card  ───────────────────────  
skill = AgentSkill(  
    id="return_pickup",  
    name="Return pick-up scheduling",  
    description="Provides slots, books, looks up or cancels product-return pick-ups.",  
    tags=["logistics", "return"],  
)  
  
PUBLIC_CARD = AgentCard(  
    name="Contoso Logistics Agent",  
    description="Cross-domain logistics service for product returns.",  
    url="http://0.0.0.0:9100/",  
    version="1.0.0",  
    defaultInputModes=["text"],  
    defaultOutputModes=["text"],  
    capabilities=AgentCapabilities(streaming=True),  
    skills=[skill],  
)  
  
# ─────────────────────────  Run server  ────────────────────────  
def main() -> None:  
    handler = DefaultRequestHandler(  
        agent_executor=LogisticsA2AExecutor(), task_store=InMemoryTaskStore()  
    )  
    app = A2AStarletteApplication(agent_card=PUBLIC_CARD, http_handler=handler)  
    uvicorn.run(app.build(), host="0.0.0.0", port=9100)  
  
  
if __name__ == "__main__":  
    main()  