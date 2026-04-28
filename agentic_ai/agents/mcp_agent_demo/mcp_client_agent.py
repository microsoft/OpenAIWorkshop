"""
Part 2 — Consume the agent-powered MCP service from another agent.

This script creates a local "Coordinator" agent that connects to the
remote Expert Advisor MCP server (Part 1) and delegates business
analysis questions to it.

Prerequisites:
    mcp_server.py must be running on http://localhost:8002/mcp

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python mcp_client_agent.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load credentials from the shared mcp/.env
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", ".env")
load_dotenv(env_path)

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient


async def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in mcp/.env")
        sys.exit(1)

    mcp_server_url = "http://localhost:8002/mcp"
    print(f"🔗 Connecting to MCP server at {mcp_server_url} ...")

    # 1) Create the MCPStreamableHTTPTool — this connects to the remote agent
    async with MCPStreamableHTTPTool(
        name="expert_advisor",
        description="Remote Expert Advisor agent accessible via MCP — can analyze risk, look up market data, and summarize findings.",
        url=mcp_server_url,
    ) as mcp_tool:
        print(f"✅ Connected! Tools available from MCP server: {[t.name for t in mcp_tool.functions]}")

        # 2) Create a local Coordinator agent that wraps the MCP tool
        client = OpenAIChatClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            model=deployment,
            api_version=api_version,
        )

        async with Agent(
            client=client,
            name="Coordinator",
            instructions=(
                "You are a project coordinator. When users ask business strategy questions, "
                "use the expert_advisor MCP tool to get expert analysis. Present the results "
                "clearly and add your own coordination notes."
            ),
            tools=mcp_tool,
        ) as coordinator:
            # 3) Ask some questions
            queries = [
                "What are the main risks if we expand into the technology sector?",
                "Give me current market data for the healthcare sector and summarize it.",
            ]

            for query in queries:
                print(f"\n{'='*60}")
                print(f"📝 User: {query}")
                print(f"{'='*60}")

                response = await coordinator.run(query)

                print(f"\n🤖 Coordinator:\n{response.text}")
                print(f"{'─'*60}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
