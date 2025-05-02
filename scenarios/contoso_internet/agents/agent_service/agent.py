import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import FunctionTool, ToolSet, CodeInterpreterTool
from fastmcp import Client  
from agents.base_agent import BaseAgent
import json

import os
import requests
from typing import Dict, Any, List, Optional

# MCP Service endpoint
MCP_ENDPOINT = os.getenv("MCP_SERVER_URI", "http://localhost:8000")
client = Client(MCP_ENDPOINT)
def _to_native(content) -> Any:  
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
        response = _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")


async def get_customer_detail(customer_id: int) -> Dict[str, Any]:
    """Get a full customer profile including their subscriptions."""
    async with client: 
        response = await client.call_tool('get_customer_detail', {"customer_id": customer_id})
        response = _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customer detail: {response['text']}")

async def get_subscription_detail(subscription_id: int) -> Dict[str, Any]:
    """Detailed subscription view → invoices (with payments) + service incidents."""        
    async with client: 
        response = await client.call_tool("get_subscription_detail", {"subscription_id": subscription_id})
        response = _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching subscription detail: {response['text']}")

async def get_promotions():
    """Get all promotions."""
    async with client:     
        response = await client.call_tool("get_promotions")
        response = _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching promotions: {response['text']}")

async def get_eligible_promotions(customer_id: int):
    """Check if a customer is eligible for a promotion."""
    async with client: 
        response = await client.call_tool("get_eligible_promotions", {"customer_id": customer_id})  
        response = _to_native(response[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching eligible promotions: {response['text']}")

async def search_knowledge_base(query: str):    
    async with client: 
        res = await client.call_tool("search_knowledge_base", {"query": query, "topk": 2})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching knowledge base: {response['text']}")
    
  
async def get_security_logs(cust_id: int):  
    async with client: 
        res = await client.call_tool("get_security_logs", {"customer_id": cust_id})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")
  
async def get_customer_orders(cust_id: int):  
    async with client: 
        res = await client.call_tool("get_customer_orders", {"customer_id": cust_id})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")

async def get_data_usage(sub_id: int):  
    async with client: 
        res = await client.call_tool("get_data_usage", {  
                    "subscription_id": sub_id,  
                    "start_date": "2023-01-01",  
                    "end_date": "2099-01-01",  
                    "aggregate": True,  
                },  )  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")

async def get_billing_summary(cust_id: int):  
    async with client: 
        res = await client.call_tool("get_billing_summary", {"customer_id": cust_id})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")
  
async def update_subscription(sub_id: int):  
    async with client: 
        res = await client.call_tool("update_subscription", {"subscription_id": sub_id, "update": {"status": "inactive"}})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")
    

async def unlock_account(cust_id: int):  
    async with client: 
        res = await client.call_tool("unlock_account", {"customer_id": cust_id})  
        response = _to_native(res[0])
        if response['status_code'] == 200:
            return response['data']
        else:
            raise Exception(f"Error fetching customers: {response['text']}")


# Add more functions as needed for all your MCP tools

import functools
import asyncio
import threading
import concurrent.futures

def make_sync_wrapper(async_func):
    """
    Convert an async function to a synchronous function with improved error handling.
    Uses a separate event loop in a dedicated thread to avoid event loop conflicts.
    """
    @functools.wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        # Create a dedicated executor for this function call
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_async_in_new_loop, async_func, *args, **kwargs)
            try:
                return future.result(timeout=60)  # Add a timeout to prevent hanging
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"Function {async_func.__name__} timed out after 60 seconds")
    
    return sync_wrapper

def _run_async_in_new_loop(async_func, *args, **kwargs):
    """Run an async function in a completely new event loop with robust error handling."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))
    except Exception as e:
        # Add more context to the exception
        raise type(e)(f"Error in {async_func.__name__}: {str(e)}") from e
    finally:
        loop.close()
# Create synchronous versions of your async functions
get_all_customers_sync = make_sync_wrapper(get_all_customers)
get_customer_detail_sync = make_sync_wrapper(get_customer_detail)
get_subscription_detail_sync = make_sync_wrapper(get_subscription_detail)
get_promotions_sync = make_sync_wrapper(get_promotions)
get_eligible_promotions_sync = make_sync_wrapper(get_eligible_promotions)
search_knowledge_base_sync = make_sync_wrapper(search_knowledge_base)
get_security_logs_sync = make_sync_wrapper(get_security_logs)
get_customer_orders_sync = make_sync_wrapper(get_customer_orders)
get_data_usage_sync = make_sync_wrapper(get_data_usage)
get_billing_summary_sync = make_sync_wrapper(get_billing_summary)
update_subscription_sync = make_sync_wrapper(update_subscription)
unlock_account_sync = make_sync_wrapper(unlock_account)

# Use synchronous versions in your tools dictionary
mcp_tools = {
    get_all_customers_sync, get_customer_detail_sync, get_subscription_detail_sync,
    get_promotions_sync, get_eligible_promotions_sync, search_knowledge_base_sync, 
    get_security_logs_sync, get_customer_orders_sync, get_data_usage_sync, 
    get_billing_summary_sync, update_subscription_sync, unlock_account_sync,
}
load_dotenv()

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
        
        # Get connection string from environment variable
        self.conn_str = os.environ.get("PROJECT_CONNECTION_STRING")
        if not self.conn_str:
            raise ValueError("PROJECT_CONNECTION_STRING environment variable is not set")
    
    async def _setup_azure_agent(self) -> None:
        """Initialize the Azure AI agent and tools if not already done."""
        if self._initialized:
            return
            
        try:
            # Setup authentication with Azure
            credential = DefaultAzureCredential()
            
            # Create AI Project client
            self.project_client = AIProjectClient.from_connection_string(
                credential=credential,
                conn_str=self.conn_str,
            )



            # Create the toolset for the agent
            code_interpreter = CodeInterpreterTool()
            functions = FunctionTool(mcp_tools)
            toolset = ToolSet()
            toolset.add(functions)            
            toolset.add(code_interpreter)

            self.project_client.agents.enable_auto_function_calls(toolset=toolset)
            # Create the agent with the MCP tools
            self.agent = self.project_client.agents.create_agent(
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
            self.project_client.agents.enable_auto_function_calls(toolset=toolset)
            
            logging.info(f"Created Azure AI agent, ID: {self.agent.id}")
            self._initialized = True
            
        except Exception as e:
            logging.error(f"Error setting up Azure AI agent: {str(e)}")
            raise
    def _get_function_parameters(self, func) -> Dict:
        """Extract function parameters for tool creation."""
        import inspect
        
        signature = inspect.signature(func)
        parameters = {}
        
        for param_name, param in signature.parameters.items():
            param_type = "string"  # Default type
            
            # Try to determine parameter type from annotations
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
            
            parameters[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name} for {func.__name__}"
            }
            
            # Mark required parameters
            if param.default == inspect.Parameter.empty:
                parameters[param_name]["required"] = True
        
        return {"type": "object", "properties": parameters}
    

    async def chat_async(self, prompt: str) -> str:
        """Process user prompt through the Azure AI agent and return the response."""
        try:
            await self._setup_azure_agent()
            
            # Create a new conversation if we don't have one yet
            if not hasattr(self, 'conversation') or self.conversation is None:
                self.conversation = self.project_client.agents.create_thread()
                logging.info(f"Created new conversation with ID: {self.conversation.id}")
            
            # Send the message to the agent
            msg = self.project_client.agents.create_message(
                thread_id=self.conversation.id,
                role="user",
                content=prompt
            )

            # Add timeout to prevent blocking indefinitely
            try:
                # Use asyncio.wait_for instead of asyncio.timeout for Python 3.10 compatibility
                if asyncio.iscoroutinefunction(self.project_client.agents.create_and_process_run):
                    run = await asyncio.wait_for(
                        self.project_client.agents.create_and_process_run(
                            thread_id=self.conversation.id,
                            agent_id=self.agent.id
                        ),
                        timeout=120  # 2-minute timeout
                    )
                else:
                    loop = asyncio.get_event_loop()
                    run = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self.project_client.agents.create_and_process_run(
                                thread_id=self.conversation.id,
                                agent_id=self.agent.id
                            )
                        ),
                        timeout=120  # 2-minute timeout
                    )
            except asyncio.TimeoutError:
                logging.error("Timeout occurred while waiting for agent response")
                return "I'm sorry, the response took too long to generate. Please try again."
                
            # Get the response
            if asyncio.iscoroutinefunction(self.project_client.agents.list_messages):
                response = await self.project_client.agents.list_messages(thread_id=self.conversation.id)
            else:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.project_client.agents.list_messages(thread_id=self.conversation.id)
                )
                
            assistant_response = response.get_last_text_message_by_role(role="assistant").text.value
            
            # Update chat history
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_response}
            ]
            self.append_to_chat_history(messages)
            
            # Save conversation state
            self._setstate(self.conversation.id)

            return assistant_response
            
        except Exception as e:
            logging.error(f"Error in chat_async: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error: {str(e)}"