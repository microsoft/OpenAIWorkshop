"""
Part 1 — Expose an Agent-Framework agent as an MCP HTTP server.

This script creates an Azure OpenAI–powered agent with domain tools,
then serves it as an MCP Streamable-HTTP endpoint on port 8002.

Any MCP client (Claude Desktop, VS Code Copilot, or another agent using
MCPStreamableHTTPTool) can connect to http://localhost:8002/mcp and
invoke the agent.

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python mcp_server.py
"""

import asyncio
import os
import sys
from typing import Annotated

from dotenv import load_dotenv

# Load credentials from the shared mcp/.env
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", ".env")
load_dotenv(env_path)

from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatClient
from mcp.server.fastmcp import FastMCP

# ── Domain tools the agent can use ──────────────────────────────────────────

@tool(approval_mode="never_require")
def analyze_risk(
    scenario: Annotated[str, "A brief description of the business scenario to assess"],
) -> Annotated[str, "A risk analysis summary"]:
    """Analyze business risk for a given scenario and return a structured assessment."""
    # Simulated risk analysis — in production this would call a model or DB
    return (
        f"Risk Analysis for: {scenario}\n"
        "─────────────────────────────\n"
        "• Market Risk: MEDIUM — competitive landscape is evolving\n"
        "• Financial Risk: LOW — strong cash position\n"
        "• Operational Risk: MEDIUM — supply chain dependencies noted\n"
        "• Regulatory Risk: LOW — compliant with current frameworks\n"
        "• Overall Rating: MEDIUM\n"
        "• Recommendation: Proceed with standard due diligence."
    )


@tool(approval_mode="never_require")
def get_market_data(
    sector: Annotated[str, "Industry sector to look up, e.g. 'technology', 'healthcare'"],
) -> Annotated[str, "Market data summary for the sector"]:
    """Retrieve current market data for a given industry sector."""
    data = {
        "technology": "Tech sector: YTD +18%, P/E 28x, top movers: AI infrastructure, cloud security.",
        "healthcare": "Healthcare sector: YTD +8%, P/E 22x, top movers: GLP-1 drugs, digital health.",
        "energy": "Energy sector: YTD +5%, P/E 14x, top movers: renewables, grid storage.",
        "finance": "Finance sector: YTD +12%, P/E 16x, top movers: fintech, digital payments.",
    }
    return data.get(sector.lower(), f"No data available for sector '{sector}'. Known sectors: {', '.join(data.keys())}")


@tool(approval_mode="never_require")
def summarize_findings(
    text: Annotated[str, "The text to summarize"],
    max_sentences: Annotated[int, "Maximum number of sentences in the summary"] = 3,
) -> Annotated[str, "A concise summary"]:
    """Produce a concise summary of the provided text."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    summary = ". ".join(sentences[:max_sentences]) + "."
    return f"Summary ({max_sentences} sentences max): {summary}"


# ── Build and serve ─────────────────────────────────────────────────────────

def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in mcp/.env")
        sys.exit(1)

    print(f"🔧 Azure OpenAI endpoint : {endpoint}")
    print(f"🔧 Deployment            : {deployment}")

    # 1) Create the agent-framework Agent
    client = OpenAIChatClient(
        api_key=api_key,
        azure_endpoint=endpoint,
        model=deployment,
        api_version=api_version,
    )

    agent = Agent(
        client=client,
        name="ExpertAdvisor",
        description=(
            "An expert business advisor that can analyze risk, retrieve market data, "
            "and summarize findings. Ask it any business strategy question."
        ),
        instructions=(
            "You are an expert business strategy advisor. Use your tools to provide "
            "thorough, data-backed analysis. Always call analyze_risk for risk questions, "
            "get_market_data for sector insights, and summarize_findings to condense results."
        ),
        tools=[analyze_risk, get_market_data, summarize_findings],
    )

    # 2) Create a FastMCP wrapper that delegates to the agent
    #    We register the agent as a single MCP tool so any MCP client can invoke it.
    mcp_server = FastMCP(
        "ExpertAdvisor",
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",
        port=8002,
    )

    @mcp_server.tool()
    async def ask_expert(
        question: Annotated[str, "The business question to ask the expert advisor"],
    ) -> str:
        """Ask the Expert Advisor agent a business strategy question. It can analyze risk, look up market data, and summarize findings."""
        async with agent:
            response = await agent.run(question)
            return response.text

    print("──────────────────────────────────────────────────")
    print("🚀 MCP Agent Server starting on http://localhost:8002/mcp")
    print("   Transport: Streamable HTTP (stateless)")
    print("   Tools exposed: ask_expert (wraps ExpertAdvisor agent)")
    print("──────────────────────────────────────────────────")

    mcp_server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
