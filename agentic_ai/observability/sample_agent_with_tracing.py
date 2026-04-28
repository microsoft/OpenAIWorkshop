# Copyright (c) Microsoft. All rights reserved.

"""
Sample agent with full observability using Application Insights.

This demonstrates how to:
1. Configure observability with Application Insights
2. Create custom spans for operations
3. Run agents with full tracing of tool calls and LLM invocations
4. View results in Grafana dashboards

Usage:
    cd agentic_ai/applications
    uv run python ../observability/sample_agent_with_tracing.py

Prerequisites:
    - Set APPLICATIONINSIGHTS_CONNECTION_STRING in .env
    - MCP server running (cd mcp && uv run python mcp_service.py)
    - Azure OpenAI credentials configured

Grafana Dashboards:
    - Agent Overview: https://aka.ms/amg/dash/af-agent
    - Workflow Overview: https://aka.ms/amg/dash/af-workflow
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
agentic_ai_dir = current_dir.parent
applications_dir = agentic_ai_dir / "applications"
sys.path.insert(0, str(agentic_ai_dir))
sys.path.insert(0, str(applications_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(applications_dir / ".env")

# Import observability BEFORE creating any agents
from observability import setup_observability, get_tracer, get_trace_id
from opentelemetry.trace import SpanKind

# Setup observability first
APPINSIGHTS_CONNECTION_STRING = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

if not APPINSIGHTS_CONNECTION_STRING:
    print("❌ APPLICATIONINSIGHTS_CONNECTION_STRING not set in environment")
    print("   Add it to agentic_ai/applications/.env")
    sys.exit(1)

success = setup_observability(
    connection_string=APPINSIGHTS_CONNECTION_STRING,
    service_name="contoso-agent-demo",
    enable_live_metrics=True,
    enable_sensitive_data=True,  # Enable to see prompts/responses (dev only!)
)

if not success:
    print("❌ Failed to configure observability")
    sys.exit(1)


async def run_agent_with_tracing():
    """Run a sample agent with full observability."""
    
    from agent_framework import Agent, MCPStreamableHTTPTool
    from agent_framework.openai import OpenAIChatClient
    from azure.identity import DefaultAzureCredential
    
    # Get tracer for custom spans
    tracer = get_tracer("contoso-agent-demo")
    
    # MCP server URL
    mcp_url = os.environ.get("MCP_SERVER_URI", "http://localhost:8000/mcp")
    
    # Azure OpenAI configuration
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
    
    if not azure_endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT not set")
        return
    
    print("=" * 60)
    print("Agent with Application Insights Observability")
    print("=" * 60)
    
    # Create a parent span for the entire session
    with tracer.start_as_current_span("customer-service-session", kind=SpanKind.SERVER) as session_span:
        trace_id = get_trace_id()
        print(f"\n📊 Trace ID: {trace_id}")
        print(f"   View in Azure Portal or Grafana after completion")
        print()
        
        # Add custom attributes to the span
        session_span.set_attribute("customer.scenario", "billing-inquiry")
        session_span.set_attribute("session.type", "demo")
        
        # Create MCP tool (connects to MCP server on demand)
        mcp_tool = MCPStreamableHTTPTool(
            name="contoso_mcp",
            url=mcp_url,
            timeout=30,
        )
        
        # Create chat client (passing azure_endpoint routes to Azure OpenAI)
        chat_client = OpenAIChatClient(
            azure_endpoint=azure_endpoint,
            model=deployment_name,
            credential=DefaultAzureCredential(),
        )
        
        # Create agent
        agent = Agent(
            client=chat_client,
            tools=[mcp_tool],
            name="CustomerServiceAgent",
            instructions="""You are a helpful customer service agent for Contoso Wireless.
            Use the available tools to look up customer information, billing details, and data usage.
            Be concise and helpful in your responses.""",
            id="customer-service-agent",
        )
        
        # Sample queries to demonstrate observability
        queries = [
            "What's the billing summary for customer 1?",
            "Show me the data usage for subscription 1 from 2025-01-01 to 2025-01-15",
        ]
        
        session = agent.create_session()
        
        for query in queries:
            print(f"\n👤 User: {query}")
            print(f"🤖 Agent: ", end="")
            
            # Each query gets its own span
            with tracer.start_as_current_span(
                "agent-query",
                kind=SpanKind.CLIENT
            ) as query_span:
                query_span.set_attribute("user.query", query)
                
                async for update in agent.run(query, session=session, stream=True):
                    if update.text:
                        print(update.text, end="")
        print("\n" + "=" * 60)
        print("✅ Session complete!")
        print(f"📊 View traces at: https://aka.ms/amg/dash/af-agent")
        print(f"   Filter by Trace ID: {trace_id}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_agent_with_tracing())
