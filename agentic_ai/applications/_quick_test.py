"""Quick 1-query test for both reflection agents."""
import asyncio, sys, warnings
from pathlib import Path
# Suppress the known MCP client library cleanup warning (same for all skills agents)
warnings.filterwarnings("ignore", message=".*async_generator.*")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv; load_dotenv()

async def test():
    q = "What is the billing summary for customer 1?"

    # Test 1: reflection_agent (baseline, no skills)
    print("=== reflection_agent (baseline) ===")
    from agents.agent_framework.multi_agent.reflection_agent import Agent as RA
    a1 = RA({}, "test-ra-001")
    r1 = await a1.chat_async(q)
    print(f"Response ({len(r1)} chars): {r1[:300]}")
    print(f"Tool calls: {[t['name'] for t in a1.get_tool_calls()]}")
    print()

    # Test 2: reflection_workflow_agent (with skills)
    print("=== reflection_workflow_agent (skills) ===")
    from agents.agent_framework.multi_agent.reflection_workflow_agent import Agent as RWA
    a2 = RWA({}, "test-rwa-001")
    r2 = await a2.chat_async(q)
    si = a2.get_skill_info()
    print(f"Skill: {si.get('skill_display_name','?')} (confidence={si.get('confidence',0):.2f})")
    print(f"Response ({len(r2)} chars): {r2[:300]}")
    print(f"Tool calls: {[t['name'] for t in a2.get_tool_calls()]}")

asyncio.run(test())
