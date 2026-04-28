"""
Stateful MCP Client — multi-turn agent-to-agent conversation.

This script demonstrates a local agent-framework Agent having a multi-turn,
stateful conversation with a remote Expert Advisor agent served via MCP.

The key insight:
  • MCPStreamableHTTPTool maintains the MCP session (sends mcp-session-id
    header automatically), so the *remote* agent remembers prior turns.
  • The local coordinator agent also maintains its own conversation context.

Prerequisites:
    mcp_server_stateful.py must be running on http://localhost:8002/mcp

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python mcp_client_stateful.py
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
    print(f"🔗 Connecting to stateful MCP server at {mcp_server_url} ...")

    # ── Connect to the stateful MCP server ──────────────────────────────
    # MCPStreamableHTTPTool maintains the MCP session automatically.
    # All calls within this context block share the same mcp-session-id,
    # so the remote agent retains conversation history.
    async with MCPStreamableHTTPTool(
        name="stateful_expert",
        description=(
            "Remote Expert Advisor agent (stateful). Supports multi-turn "
            "conversations — the expert remembers what was discussed earlier. "
            "Tools: chat_with_expert, get_session_info, reset_conversation."
        ),
        url=mcp_server_url,
    ) as mcp_tool:
        tool_names = [t.name for t in mcp_tool.functions]
        print(f"✅ Connected! Tools available: {tool_names}")

        # ── Create the local coordinator agent ──────────────────────────
        client = OpenAIChatClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            model=deployment,
            api_version=api_version,
        )

        async with Agent(
            client=client,
            name="MultiTurnCoordinator",
            instructions=(
                "You coordinate multi-turn conversations with a remote expert advisor.\n\n"
                "RULES:\n"
                "1. When the user asks a question, use the chat_with_expert tool to send it.\n"
                "2. The expert remembers previous turns — you can ask follow-up questions.\n"
                "3. Present the expert's response clearly, adding brief coordination notes.\n"
                "4. If asked for session info, use the get_session_info tool.\n"
                "5. If asked to reset, use the reset_conversation tool.\n"
                "6. Do NOT repeat the full question in your tool call — keep it concise."
            ),
            tools=mcp_tool,
        ) as coordinator:

            # ── Multi-turn conversation ─────────────────────────────────
            # Each question builds on the previous one. The remote expert
            # maintains state across calls thanks to the stateful MCP session.
            conversation = [
                "What are the main risks if we expand into the technology sector?",
                "Based on that risk analysis, what does current market data for technology look like? Are the risks justified by the opportunity?",
                "Now summarize everything we've discussed — the risks AND the market data — into a brief executive recommendation.",
            ]

            for i, question in enumerate(conversation, 1):
                print(f"\n{'='*70}")
                print(f"  TURN {i}")
                print(f"{'='*70}")
                print(f"📝 User: {question}\n")

                response = await coordinator.run(question)

                print(f"🤖 Coordinator:\n{response.text}")
                print(f"{'─'*70}")

            # ── Show session metadata ───────────────────────────────────
            print(f"\n{'='*70}")
            print("  SESSION INFO")
            print(f"{'='*70}")
            info_response = await coordinator.run(
                "Use the get_session_info tool and tell me how many turns we've had."
            )
            print(f"📊 {info_response.text}")

    print("\n✅ Stateful multi-turn demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
