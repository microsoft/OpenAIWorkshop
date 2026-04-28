"""
Part 9 — Conversational Group Chat: User ↔ Local Agent + LangGraph Agent

Demonstrates MAF's GroupChatBuilder orchestrating a multi-agent
discussion between:

  👔 BusinessStrategist  — local MAF agent (Azure OpenAI)
  🏗️  TechnicalArchitect  — LangGraph agent served via MCP (port 8003)
  📋 Planner             — local MAF agent that synthesizes the plan
  🎯 Facilitator         — LLM orchestrator that decides who speaks next

The Facilitator routes the conversation: experts discuss first, then
the Planner delivers a consolidated plan inline — no separate
synthesis step needed.  This is more efficient than post-hoc synthesis.

Simulates a multi-turn conversation with predefined questions:
  1. User poses an initial topic → experts discuss → Planner delivers plan
  2. User asks a follow-up → experts discuss deeper → Planner updates plan
  3. The TechnicalArchitect (LangGraph) remembers prior turns
     via MemorySaver — the proxy sends only the NEW message

This showcases stateful cross-framework orchestration:
  • MCP session provides a persistent connection
  • LangGraph MemorySaver keeps conversation history server-side
  • MCPProxyAgent sends only the latest message (not full history)
  • GroupChatBuilder treats both local and remote agents identically
  • Planner delivers the plan as a participant (no extra LLM call)

Prerequisites:
    mcp_server_langgraph.py must be running on http://localhost:8003/mcp

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python workflow_group_chat.py
"""

import asyncio
import os
import sys
import uuid
from typing import Any, cast

from dotenv import load_dotenv

# Load credentials from the shared mcp/.env
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", ".env")
load_dotenv(env_path)

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    BaseAgent,
    Content,
    MCPStreamableHTTPTool,
    Message,
)
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import GroupChatBuilder


# ═══════════════════════════════════════════════════════════════════════════
#  MCPProxyAgent — BaseAgent that bridges to a remote MCP tool
# ═══════════════════════════════════════════════════════════════════════════


class MCPProxyAgent(BaseAgent):
    """BaseAgent that forwards the latest message to a remote MCP tool.

    Because the MCP server is **stateful** (maintains conversation history
    per session via MemorySaver), we only need to send the LATEST message
    — not the full conversation history.  The server accumulates context
    automatically.
    """

    def __init__(
        self,
        *,
        mcp_tool: MCPStreamableHTTPTool,
        tool_name: str,
        name: str = "mcp_proxy",
        description: str | None = None,
        param_name: str = "question",
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, description=description, **kwargs)
        self._mcp_tool = mcp_tool
        self._tool_name = tool_name
        self._param_name = param_name

    # Must be a regular def — GroupChatBuilder iterates with
    # ``async for update in agent.run(stream=True)``
    def run(self, messages: Any = None, *, stream: bool = False, **kwargs: Any) -> Any:
        if stream:
            return self._run_stream(messages)
        return self._run_impl(messages)

    async def _run_impl(self, messages: Any) -> AgentResponse:
        result_text = await self._call(messages)
        return AgentResponse(
            messages=[Message("assistant", [result_text], author_name=self.name)],
            response_id=f"proxy-{uuid.uuid4().hex[:8]}",
            agent_id=self.id,
        )

    async def _run_stream(self, messages: Any):
        result_text = await self._call(messages)
        yield AgentResponseUpdate(
            contents=[Content.from_text(result_text)],
            role="assistant",
            author_name=self.name,
            agent_id=self.id,
            response_id=f"proxy-{uuid.uuid4().hex[:8]}",
        )

    async def _call(self, messages: Any) -> str:
        """Extract only the LATEST message and forward to the stateful MCP tool.

        The server-side LangGraph agent (with MemorySaver) already has the
        full conversation history for this session, so we only send the
        new content.  This is the key difference from the old implementation
        which manually forwarded the entire conversation each turn.
        """
        latest_text = _extract_latest_message(messages)
        result = await self._mcp_tool.call_tool(
            self._tool_name, **{self._param_name: latest_text}
        )
        if isinstance(result, (list, tuple)):
            return "\n".join(
                c.text for c in result if hasattr(c, "text") and c.text
            ) or str(result)
        return result.text if hasattr(result, "text") and result.text else str(result)


def _extract_latest_message(messages: Any) -> str:
    """Extract just the last meaningful message from the conversation.

    The orchestrator passes the full conversation as list[Message].
    We only need the LAST message since the MCP server is stateful
    and already has prior turns in its MemorySaver checkpointer.
    """
    if isinstance(messages, str):
        return messages
    if isinstance(messages, Message):
        return messages.text or ""
    if isinstance(messages, (list, tuple)):
        # Walk backwards to find the last message with content
        for m in reversed(messages):
            if isinstance(m, Message):
                text = m.text or ""
                if text.strip():
                    name = m.author_name or m.role or "someone"
                    return f"[{name}]: {text}"
            elif isinstance(m, str) and m.strip():
                return m
    return str(messages) if messages else ""


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN — Conversational Group Chat with follow-ups
# ═══════════════════════════════════════════════════════════════════════════


async def _run_group_chat(
    topic: str,
    strategist: Any,
    architect: MCPProxyAgent,
    planner: Any,
    facilitator: Any,
    turn_label: str = "Initial Discussion",
) -> int:
    """Run one round of group chat.

    Returns:
        round_count — number of visible participant messages.
    """
    workflow = GroupChatBuilder(
        participants=[strategist, architect, planner],
        orchestrator_agent=facilitator,
        max_rounds=6,
        intermediate_outputs=True,
    ).build()

    print()
    print(f"━{'━' * 76}━")
    print(f"  📋 {turn_label}")
    print(f"━{'━' * 76}━")
    print(f"  {topic[:120]}{'…' if len(topic) > 120 else ''}")
    print()

    round_num = 0
    async for event in workflow.run(topic, stream=True):
        if event.type == "output":
            data = event.data
            if not isinstance(data, list):
                continue
            for msg in cast(list[Message], data):
                name = msg.author_name or ""
                text = msg.text or ""
                if not text.strip():
                    continue

                # Skip the initial user message echo
                if not name or msg.role == "user":
                    continue

                if name == "BusinessStrategist":
                    icon, framework = "👔", "MAF Agent"
                elif name == "TechnicalArchitect":
                    icon, framework = "🏗️", "LangGraph via MCP"
                elif name == "Planner":
                    icon, framework = "📋", "MAF Agent"
                else:
                    icon, framework = "💬", name

                round_num += 1
                print(f"{'═' * 78}")
                print(f"  Round {round_num} — {icon} {name}  [{framework}]")
                print(f"{'═' * 78}")
                print()
                print(text)
                print()

    return round_num





# ═══════════════════════════════════════════════════════════════════════════
#  Predefined conversation — simulates a multi-turn user interaction
# ═══════════════════════════════════════════════════════════════════════════

CONVERSATION = [
    {
        "role": "user",
        "label": "Initial Topic",
        "message": (
            "Our company is a mid-size e-commerce retailer with a legacy "
            "on-premise monolithic Java application serving 2M monthly users. "
            "We want to migrate to a cloud-native architecture to improve "
            "scalability, reduce operational costs, and enable AI-powered "
            "personalization. We have a $500K budget and 12-month timeline. "
            "Discuss the strategy, architecture, and implementation approach."
        ),
    },
    {
        "role": "user",
        "label": "Follow-up: Risk & Phasing",
        "message": (
            "Thanks for the plan. I have concerns about risk. "
            "What are the biggest risks with this migration, and how "
            "should we phase the rollout to minimize disruption to our "
            "existing customers? Can we keep the monolith running in "
            "parallel during the transition?"
        ),
    },
]


async def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in mcp/.env")
        sys.exit(1)

    mcp_server_url = "http://localhost:8003/mcp"

    print("=" * 78)
    print("🗣️  Conversational Group Chat — User ↔ MAF + LangGraph Agents")
    print("=" * 78)
    print()
    print("  Simulating a multi-turn conversation with predefined questions.")
    print("  The TechnicalArchitect (LangGraph) remembers prior turns via")
    print("  MemorySaver — the proxy sends only the NEW message each turn.")
    print()

    # ── Connect to the stateful LangGraph MCP server ─────────────────────
    async with MCPStreamableHTTPTool(
        name="technical_architect",
        description="Remote Technical Architect (LangGraph) via MCP",
        url=mcp_server_url,
    ) as mcp_tool:
        print(f"🔗 Connected to LangGraph MCP server at {mcp_server_url}")
        print(f"   Available tools: {[t.name for t in mcp_tool.functions]}")
        print(f"   Session: stateful (server maintains conversation history)")
        print()

        client = OpenAIChatClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            model=deployment,
            api_version=api_version,
        )

        # ── Participant 1: Local Business Strategist (MAF Agent) ─────────
        strategist = client.as_agent(
            name="BusinessStrategist",
            instructions=(
                "You are a Business Strategist specializing in digital "
                "transformation and cloud migration. Focus on:\n"
                "• Business impact and ROI analysis\n"
                "• Customer experience implications\n"
                "• Risk mitigation and change management\n"
                "• Competitive advantage and market positioning\n"
                "• Timeline and budget considerations\n\n"
                "Build on what others have said in the conversation. "
                "Be concise but insightful — 2-3 paragraphs max."
            ),
        )

        # ── Participant 2: Remote Technical Architect (LangGraph via MCP) ─
        architect = MCPProxyAgent(
            mcp_tool=mcp_tool,
            tool_name="ask_architect",
            param_name="question",
            name="TechnicalArchitect",
            description=(
                "Technical Architect providing architecture design, "
                "technology stack recommendations, cloud infrastructure "
                "planning, and migration strategies. Built with LangGraph, "
                "served via MCP."
            ),
        )

        # ── Participant 3: Planner (synthesizes discussion into plan) ────
        planner = client.as_agent(
            name="Planner",
            instructions=(
                "You are a senior project planner participating in a "
                "strategy meeting alongside a BusinessStrategist and "
                "TechnicalArchitect.\n\n"
                "When the facilitator calls on you, synthesize the team's "
                "discussion into a structured, actionable plan:\n"
                "  • Numbered phases with clear deliverables\n"
                "  • Timeline and budget allocation\n"
                "  • Key milestones and success metrics\n"
                "  • Top risks with mitigations\n"
                "  • Concrete next steps\n\n"
                "Incorporate BOTH business and technical recommendations "
                "from your teammates. Write it as a professional plan "
                "the client can act on. Be comprehensive but concise."
            ),
        )

        # ── Orchestrator: Lightweight Facilitator ─────────────────────────
        facilitator = client.as_agent(
            name="Facilitator",
            instructions=(
                "You are a discussion facilitator for a strategy meeting. "
                "Three experts are available:\n\n"
                "  • BusinessStrategist — business impact, ROI, risk, "
                "go-to-market\n"
                "  • TechnicalArchitect — architecture, tech stack, "
                "migration patterns, infrastructure\n"
                "  • Planner — synthesizes discussion into an actionable "
                "plan\n\n"
                "Your workflow:\n"
                "  1. Start with BusinessStrategist for business perspective\n"
                "  2. Then TechnicalArchitect for technical depth\n"
                "  3. Alternate if needed for a richer discussion\n"
                "  4. When both experts have contributed enough, call on "
                "Planner to deliver the consolidated plan\n"
                "  5. After Planner delivers the plan, TERMINATE\n\n"
                "Do NOT let Planner speak until the experts have "
                "had a meaningful exchange."
            ),
        )

        # ── Print participant info ────────────────────────────────────────
        print("━" * 78)
        print("👥 PARTICIPANTS")
        print("━" * 78)
        print("   👔 BusinessStrategist — local MAF agent (Azure OpenAI)")
        print("   🏗️  TechnicalArchitect — LangGraph agent via MCP (port 8003)")
        print("   📋 Planner           — local MAF agent (synthesizes plan)")
        print("   🎯 Facilitator       — LLM orchestrator (decides who speaks)")
        print("━" * 78)
        print()

        # ── Run the predefined conversation ───────────────────────────────
        total_rounds = 0

        for turn_num, turn in enumerate(CONVERSATION, 1):
            is_last_turn = turn_num == len(CONVERSATION)

            # Print what the "user" is saying
            print()
            print(f"{'▓' * 78}")
            print(f"  👤 USER (Turn {turn_num})")
            print(f"{'▓' * 78}")
            print(f"  {turn['message']}")
            print()

            rounds = await _run_group_chat(
                turn["message"], strategist, architect, planner,
                facilitator,
                turn_label=f"Discussion #{turn_num}: {turn['label']}",
            )
            total_rounds += rounds

            print("━" * 78)
            print(f"✅  Discussion #{turn_num} complete — {rounds} rounds.")
            print("━" * 78)

            if not is_last_turn:
                print()
                print("━" * 78)
                print("  💡 The TechnicalArchitect remembers the prior discussion")
                print("     (stateful MCP session with LangGraph MemorySaver)")
                print("     Only the NEW question is sent — server keeps history.")
                print()
                print("  📝 The user reviews the plan and asks a follow-up...")
                print("━" * 78)

        # ── Summary ──────────────────────────────────────────────────────
        print()
        print("=" * 78)
        print(f"📊  Session Summary: {len(CONVERSATION)} discussions, {total_rounds} total rounds")
        print("=" * 78)
        print("   Key points demonstrated:")
        print("     • Multi-turn conversation with predefined questions")
        print("     • Planner delivers plan inline — no separate synthesis step")
        print("     • Facilitator orchestrates: experts discuss → Planner delivers")
        print("     • LangGraph agent remembers prior context (MemorySaver)")
        print("     • MCP session provides persistent stateful connection")
        print("     • Proxy sends only latest message (server keeps history)")
        print("     • Cross-framework: MAF orchestrator + LangGraph agent via MCP")
        print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
