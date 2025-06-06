import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Set, Callable
from dotenv import load_dotenv
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.models import (
    AsyncAgentEventHandler,
    AsyncFunctionTool,
    AsyncToolSet,
    MessageDeltaChunk,
    RequiredFunctionToolCall,
    RunStep,
    SubmitToolOutputsAction,
    ThreadMessage,
    ThreadRun,
    ToolOutput
)
from fastmcp import Client
from agents.base_agent import BaseAgent
import json

# MCP Service endpoint
MCP_ENDPOINT = os.getenv("MCP_SERVER_URI", "http://localhost:8000")
client = Client(MCP_ENDPOINT)

async def _to_native(content) -> Any:
    """Return native python object (dict/list/str) regardless of TextContent/JsonContent"""
    try:
        return content.as_json()
    except Exception:
        try:
            return json.loads(content.text)
        except Exception:
            return content.text

async def get_all_customers():
    """List all customers with basic info."""
    async with client:
        response = await client.call_tool("get_all_customers")
        # Use the direct text response as in teststream.py
        return response[0].text

async def get_customer_detail(customer_id: int) -> Dict[str, Any]:
    """Get a full customer profile including their subscriptions."""
    async with client:
        # Use the correct parameter format with "params" wrapper
        response = await client.call_tool("get_customer_detail", {"params": {"customer_id": customer_id}})
        return response[0].text

async def get_subscription_detail(subscription_id: int) -> Dict[str, Any]:
    """Detailed subscription view → invoices (with payments) + service incidents."""
    async with client:
        # Use the correct parameter format with "params" wrapper
        response = await client.call_tool("get_subscription_detail", {"params": {"subscription_id": subscription_id}})
        return response[0].text

async def get_promotions():
    """Get all promotions."""
    async with client:
        response = await client.call_tool("get_promotions")
        response = await _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching promotions: {response['text']}")

async def get_eligible_promotions(customer_id: int):
    """Check if a customer is eligible for a promotion."""
    async with client:
        # Use the correct parameter format with "params" wrapper
        response = await client.call_tool("get_eligible_promotions", {"params": {"customer_id": customer_id}})
        response = await _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching eligible promotions: {response['text']}")

async def search_knowledge_base(query: str):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("search_knowledge_base", {"params": {"query": query, "topk": 2}})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching knowledge base: {response['text']}")

async def get_security_logs(cust_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("get_security_logs", {"params": {"customer_id": cust_id}})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching security logs: {response['text']}")

async def get_customer_orders(cust_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("get_customer_orders", {"params": {"customer_id": cust_id}})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customer orders: {response['text']}")

async def get_data_usage(sub_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("get_data_usage", {"params": {
            "subscription_id": sub_id,
            "start_date": "2023-01-01",
            "end_date": "2099-01-01",
            "aggregate": True,
        }})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching data usage: {response['text']}")

async def get_billing_summary(cust_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        response = await client.call_tool("get_billing_summary", {"params": {"customer_id": cust_id}})
        # Return the direct text response as in teststream.py
        return response[0].text

async def update_subscription(sub_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("update_subscription", {"params": {
            "subscription_id": sub_id,
            "update": {"status": "inactive"}
        }})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error updating subscription: {response['text']}")

async def unlock_account(cust_id: int):
    async with client:
        # Use the correct parameter format with "params" wrapper
        res = await client.call_tool("unlock_account", {"params": {"customer_id": cust_id}})
        response = await _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error unlocking account: {response['text']}")

# Define the set of async functions directly
user_async_functions: Set[Callable[..., Any]] = {
    get_all_customers,
    get_customer_detail,
    get_subscription_detail,
    get_promotions,
    get_eligible_promotions,
    search_knowledge_base,
    get_security_logs,
    get_customer_orders,
    get_data_usage,
    get_billing_summary,
    update_subscription,
    unlock_account
}

class ContosoAgentEventHandler(AsyncAgentEventHandler[str]):
    """Custom event handler for the Contoso agent streaming responses."""

    def __init__(self, functions: AsyncFunctionTool, project_client: AIProjectClient, 
                 response_container: List[str]) -> None:
        super().__init__()
        self.functions = functions
        self.project_client = project_client
        self.response_container = response_container

    async def on_message_delta(self, delta: "MessageDeltaChunk") -> None:
        if delta.text:
            self.response_container.append(delta.text)
            logging.debug(f"Text delta received: {delta.text}")

    async def on_thread_message(self, message: "ThreadMessage") -> None:
        logging.debug(f"ThreadMessage created. ID: {message.id}, Status: {message.status}")

    async def on_thread_run(self, run: "ThreadRun") -> None:
        logging.debug(f"ThreadRun status: {run.status}")

        if run.status == "failed":
            logging.error(f"Run failed. Error: {run.last_error}")

        if run.status == "requires_action" and isinstance(run.required_action, SubmitToolOutputsAction):
            tool_calls = run.required_action.submit_tool_outputs.tool_calls

            tool_outputs = []
            for tool_call in tool_calls:
                if isinstance(tool_call, RequiredFunctionToolCall):
                    try:
                        output = await self.functions.execute(tool_call)
                        tool_outputs.append(
                            ToolOutput(
                                tool_call_id=tool_call.id,
                                output=output,
                            )
                        )
                    except Exception as e:
                        logging.error(f"Error executing function '{tool_call.function.name}': {str(e)}")
                        tool_outputs.append(
                            ToolOutput(
                                tool_call_id=tool_call.id,
                                output=json.dumps({"error": str(e)}),
                            )
                        )

            logging.debug(f"Tool outputs: {tool_outputs}")
            if tool_outputs:
                await self.project_client.agents.submit_tool_outputs_to_stream(
                    thread_id=run.thread_id, run_id=run.id, tool_outputs=tool_outputs, event_handler=self
                )

    async def on_run_step(self, step: "RunStep") -> None:
        logging.debug(f"RunStep type: {step.type}, Status: {step.status}")

    async def on_error(self, data: str) -> None:
        logging.error(f"An error occurred. Data: {data}")
        self.response_container.append(f"I encountered an error: {data}")

    async def on_done(self) -> None:
        logging.debug("Stream completed.")

    async def on_unhandled_event(self, event_type: str, event_data: Any) -> None:
        logging.debug(f"Unhandled Event Type: {event_type}, Data: {event_data}")

class Agent(BaseAgent):
    """
    Azure AI Agent implementation using Azure AI Projects API.
    Inherits from BaseAgent to handle environment variables, state store, 
    and chat history management.
    """
    
    def __init__(self, state_store: Dict[str, Any], session_id: str) -> None:
        """Initialize the Azure AI Agent with state storage and session identifier."""
        super().__init__(state_store, session_id)
        self.project_client = None
        self.agent = None
        self._initialized = False
        self.conversation = None
        self.conversation_id = None
        
        # Store the conversation ID from state, but don't create the conversation object yet
        # We'll create/retrieve it properly in chat_async
        if self.state is not None:
            self.conversation_id = self.state
            logging.info(f"Found stored conversation ID: {self.conversation_id}")
        
        # Get connection string from environment variable
        self.conn_str = os.environ.get("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
        if not self.conn_str:
            raise ValueError("PROJECT_CONNECTION_STRING environment variable is not set")
    
    async def _setup_azure_agent(self) -> None:
        """Initialize the Azure AI agent and tools if not already done."""
        if self._initialized:
            return
            
        try:
            # Setup authentication with Azure
            credential = DefaultAzureCredential()
            
            # Create AI Project client - using the async version from .aio
            self.project_client = AIProjectClient.from_connection_string(
                credential=credential,
                conn_str=self.conn_str,
            )

            # Initialize agent toolset with user async functions directly
            functions = AsyncFunctionTool(user_async_functions)
            toolset = AsyncToolSet()
            toolset.add(functions)
            
            # Enable auto function calls - remove await as this method doesn't return a coroutine
            self.project_client.agents.enable_auto_function_calls(toolset=toolset)
            
            # Create the agent with the tools - await for async call
            self.agent = await self.project_client.agents.create_agent(
                model=self.openai_model_name, 
                name="Contoso Customer Assistant",
                instructions=(
                    "You are a customer service assistant for Contoso Internet. "
                    "Use the provided functions to access customer data, subscriptions, "
                    "billing information, and the knowledge base. "
                    "Always address customer inquiries professionally and accurately."
                ),
                toolset=toolset
            )
            
            logging.info(f"Created Azure AI agent, ID: {self.agent.id}")
            self._initialized = True
            
        except Exception as e:
            logging.error(f"Error setting up Azure AI agent: {str(e)}")
            raise

    async def chat_async(self, prompt: str) -> str:
        """Process user prompt through the Azure AI agent and return the response."""
        try:
            await self._setup_azure_agent()
            
            # If we have a conversation ID but no conversation object, get the thread
            if self.conversation is None:
                if self.conversation_id is not None:
                    # Get the existing thread using the stored ID
                    self.conversation = await self.project_client.agents.get_thread(thread_id=self.conversation_id)
                    logging.info(f"Retrieved existing conversation with ID: {self.conversation.id}")
                else:
                    # Create a new conversation if we don't have one
                    self.conversation = await self.project_client.agents.create_thread()
                    logging.info(f"Created new conversation with ID: {self.conversation.id}")
            
            # Send the message to the agent
            await self.project_client.agents.create_message(
                thread_id=self.conversation.id,
                role="user",
                content=prompt
            )
            # Initialize response container for event handler
            response_container = []
            
            # Create event handler to process stream and collect responses
            event_handler = ContosoAgentEventHandler(
                AsyncFunctionTool(user_async_functions),
                self.project_client,
                response_container
            )
            
            # Process the conversation with streaming
            try:
                async with await self.project_client.agents.create_stream(
                    thread_id=self.conversation.id, 
                    agent_id=self.agent.id, 
                    event_handler=event_handler,
                    timeout=120  # 2-minute timeout
                ) as stream:
                    await stream.until_done()
            except asyncio.TimeoutError:
                logging.error("Timeout occurred while waiting for agent response")
                return "I'm sorry, the response took too long to generate. Please try again."
            
            # Get the final response from the agent
            messages = await self.project_client.agents.list_messages(thread_id=self.conversation.id)
            assistant_response = messages.get_last_text_message_by_role(role="assistant").text.value
            
            # Update chat history
            messages_to_save = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_response}
            ]
            self.append_to_chat_history(messages_to_save)
            
            # Save conversation state
            self._setstate(self.conversation.id)

            return assistant_response
            
        except Exception as e:
            logging.error(f"Error in chat_async: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error: {str(e)}"