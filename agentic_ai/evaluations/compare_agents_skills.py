"""
A/B Evaluation: Single Agent (Baseline) vs Single Agent with Skills (Variant)

Runs both agents on the same eval dataset and compares:
- Context size and token usage
- Latency (time-to-first-token, total time)
- Task success and accuracy
- Cost estimates ($)
- Tool call precision (no unnecessary calls)

Usage:
    python compare_agents_skills.py --baseline agents.agent_framework.single_agent \
                                     --variant agents.agent_framework.single_agent_skills \
                                     --dataset agentic_ai/evaluations/eval_dataset.json \
                                     --sample 0.5 \
                                     --output metrics_comparison.json
"""

import asyncio
import json
import logging
import argparse
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

# Suppress known MCP client library cleanup warnings (harmless async generator
# teardown in wrong task — library bug, fires only at process exit)
warnings.filterwarnings("ignore", message=".*async_generator.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*cancel scope.*")
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# ---------------------------------------------------------------------------
# Path setup + env loading (mirrors run_batch_eval.py)
# ---------------------------------------------------------------------------
_AGENTIC_AI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_AGENTIC_AI_ROOT / "applications"))
sys.path.insert(0, str(_AGENTIC_AI_ROOT))

from dotenv import load_dotenv
load_dotenv(_AGENTIC_AI_ROOT / "applications" / ".env")
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics for a single test case run."""
    test_id: str
    agent_variant: str  # "baseline" or "skills"
    query: str
    success: bool
    response: str
    
    # Context metrics
    instruction_size_chars: int  # length of system prompt/instructions
    instruction_size_tokens: int  # estimated tokens (approximately 1 token per 4 chars)
    
    # Request metrics
    input_tokens: int  # instruction + query
    query_tokens: int  # user query size
    response_tokens: int  # response size
    total_request_tokens: int  # query + response
    
    # Latency metrics
    latency_ms: float  # total end-to-end time in ms
    
    # Tool metrics
    tool_calls_count: int
    tool_call_names: List[str]
    irrelevant_tool_calls_count: int

    # Tool-context metrics (new)
    tools_exposed_count: int = 0              # number of tools visible in the schema
    tool_schema_tokens: int = 0               # estimated tokens consumed by tool schemas
    required_tool_coverage: float = 1.0       # fraction of required_tools that were called

    # Cross-domain / grounding metrics (new)
    cross_domain_calls_count: int = 0         # tool calls outside the test's expected domain
    grounded_answer: bool = False             # success AND required_tool_coverage > 0

    # Quality metrics
    domain_detected: Optional[str] = None  # for skills-based variant
    hallucination_detected: bool = False
    tool_precision: float = 1.0  # measure of tool call appropriateness (1.0 = perfect)

    # Cost estimate
    cost_estimate_usd: float = 0.0  # rough estimate based on token usage

    @property
    def effective_context_size(self) -> int:
        """Total context including instruction, tool schemas, and query."""
        return self.instruction_size_tokens + self.tool_schema_tokens + self.query_tokens

    @property
    def total_input_with_tools(self) -> int:
        return self.input_tokens + self.tool_schema_tokens


# ---------------------------------------------------------------------------
# Domain tool sets (mirrors SkillRegistry — used to detect cross-domain calls)
# ---------------------------------------------------------------------------
_DOMAIN_TOOLS: Dict[str, List[str]] = {
    "billing": [
        "get_all_customers", "get_customer_detail", "get_subscription_detail",
        "get_billing_summary", "get_invoice_payments", "pay_invoice",
        "get_data_usage", "update_subscription", "search_knowledge_base",
    ],
    "product": [
        "get_products", "get_product_detail", "get_promotions",
        "get_eligible_promotions", "get_customer_orders", "search_knowledge_base",
    ],
    "security": [
        "get_security_logs", "unlock_account", "get_support_tickets",
        "create_support_ticket", "search_knowledge_base",
    ],
}
# Maps eval dataset category values to domain keys above
_CATEGORY_TO_DOMAIN: Dict[str, str] = {
    "billing": "billing",
    "account": "billing",
    "internet": "product",
    "mobile": "product",
    "tv": "product",
    "bundle": "product",
    "security": "security",
    "support": "security",
}

# Approximate tokens consumed by a single tool schema entry in the prompt.
# Based on typical MCP tool schemas (~300-400 chars / 75-100 tokens).
_TOKENS_PER_TOOL_SCHEMA = 80
# Baseline agents expose the full MCP tool catalogue; verified at 18 at time of writing.
_BASELINE_TOOL_COUNT = 18


def _compute_determinism(runs: List["MetricSnapshot"]) -> Dict[str, float]:
    """Determinism metrics across N repeated runs of the same test.

    Returns keys:
        tool_set_jaccard      — mean pairwise Jaccard of tool sets (1.0 = identical)
        tool_order_match_rate — fraction of run pairs with identical call sequence
        coverage_stdev        — stdev of required_tool_coverage across runs
        success_rate          — fraction of runs that succeeded
        latency_stdev_ms      — stdev of end-to-end latency
    """
    if not runs:
        return {
            "tool_set_jaccard": 0.0,
            "tool_order_match_rate": 0.0,
            "coverage_stdev": 0.0,
            "success_rate": 0.0,
            "latency_stdev_ms": 0.0,
        }
    n = len(runs)
    if n == 1:
        return {
            "tool_set_jaccard": 1.0,
            "tool_order_match_rate": 1.0,
            "coverage_stdev": 0.0,
            "success_rate": 1.0 if runs[0].success else 0.0,
            "latency_stdev_ms": 0.0,
        }

    tool_sets = [set(r.tool_call_names) for r in runs]
    tool_seqs = [tuple(r.tool_call_names) for r in runs]

    jaccards: List[float] = []
    order_matches: List[int] = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = tool_sets[i], tool_sets[j]
            union = a | b
            jaccards.append(len(a & b) / len(union) if union else 1.0)
            order_matches.append(1 if tool_seqs[i] == tool_seqs[j] else 0)

    coverages = [r.required_tool_coverage for r in runs]
    latencies = [r.latency_ms for r in runs]
    mean_cov = sum(coverages) / n
    mean_lat = sum(latencies) / n
    cov_var = sum((c - mean_cov) ** 2 for c in coverages) / n
    lat_var = sum((l - mean_lat) ** 2 for l in latencies) / n

    return {
        "tool_set_jaccard": round(sum(jaccards) / len(jaccards), 3),
        "tool_order_match_rate": round(sum(order_matches) / len(order_matches), 3),
        "coverage_stdev": round(cov_var ** 0.5, 3),
        "success_rate": round(sum(1 for r in runs if r.success) / n, 3),
        "latency_stdev_ms": round(lat_var ** 0.5, 1),
    }


def _serialize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a result entry (with MetricSnapshot objects) into JSON-safe dicts."""
    out: Dict[str, Any] = {
        "test_id": entry["test_id"],
        "baseline": asdict(entry["baseline"]),
        "skills": asdict(entry["skills"]),
    }
    if "baseline_runs" in entry:
        out["baseline_runs"] = [asdict(s) for s in entry["baseline_runs"]]
        out["skills_runs"] = [asdict(s) for s in entry["skills_runs"]]
        out["determinism"] = entry.get("determinism", {})
    return out


class AgentEvaluator:
    """Run single test case against both agent variants and collect metrics."""

    # Azure OpenAI pricing (update based on your deployment)
    PRICING = {
        "input_per_1k_tokens": 0.003,  # GPT-4 typical input pricing
        "output_per_1k_tokens": 0.006,  # GPT-4 typical output pricing
    }
    
    def __init__(self, baseline_module: str, variant_module: str):
        self.baseline_module = baseline_module
        self.variant_module = variant_module
        self.state_store: Dict[str, Any] = {}
        self.session_counter = 0

    def _estimate_tokens(self, text) -> int:
        """Rough token estimation: ~1 token per 4 characters."""
        char_count = text if isinstance(text, int) else len(text)
        return max(1, char_count // 4)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token counts."""
        input_cost = (input_tokens / 1000) * self.PRICING["input_per_1k_tokens"]
        output_cost = (output_tokens / 1000) * self.PRICING["output_per_1k_tokens"]
        return input_cost + output_cost

    def _count_out_of_domain_calls(
        self, tool_call_names: List[str], category: str, active_skill: Optional[str] = None
    ) -> int:
        """
        Count tool calls that belong to a DIFFERENT skill domain than the test category.

        This is the correct way to measure skills effectiveness: a billing query
        should never call get_security_logs. Calling get_invoice_payments on a
        billing query is fine even if it wasn't in expected_tools.

        For the skills agent, the active_skill is the detected domain — we use
        that as the allowed domain. For the baseline, we use the test category.
        """
        domain = active_skill if active_skill else _CATEGORY_TO_DOMAIN.get(category, "billing")
        allowed = set(_DOMAIN_TOOLS.get(domain, []))
        if not allowed:
            return 0
        return sum(1 for name in tool_call_names if name not in allowed)

    def _detect_hallucination(self, response: str, allowed_keywords: List[str] = None) -> bool:
        """Simple hallucination detection: check if response claims unsupported actions."""
        hallucination_markers = [
            "i will process",
            "i will transfer",
            "accessing database",
            "updating system",
            "sending email",
        ]
        response_lower = response.lower()
        
        for marker in hallucination_markers:
            if marker in response_lower:
                # Check if response actually calls a tool vs just claiming to
                if "(" not in response_lower:  # simple heuristic
                    return True
        
        return False

    async def _import_agent_class(self, agent_variant: str):
        """Dynamically import and return the agent class for the given variant."""
        import importlib
        module_path = self.baseline_module if agent_variant == "baseline" else self.variant_module
        try:
            mod = importlib.import_module(module_path)
            return mod.Agent
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import {module_path}: {e}")
            raise

    def _build_snapshot(
        self,
        agent_variant: str,
        test_case: Dict[str, Any],
        agent,
        all_responses: List[str],
        all_tool_names: List[str],
        total_latency_ms: float,
        success: bool,
    ) -> MetricSnapshot:
        """Build a MetricSnapshot from aggregated turn data."""
        if agent_variant == "skills":
            skill_info = agent.get_skill_info() if hasattr(agent, "get_skill_info") else {}
            detected_domain = skill_info.get("skill_name")
            instruction_size_chars = skill_info.get("instruction_chars", 2500)
            tools_exposed_count = len(skill_info.get("allowed_tools", []) or []) or _BASELINE_TOOL_COUNT
        else:
            detected_domain = None
            instruction_size_chars = 2000
            tools_exposed_count = _BASELINE_TOOL_COUNT

        tool_schema_tokens = tools_exposed_count * _TOKENS_PER_TOOL_SCHEMA

        category = test_case.get("category", "")
        combined_query = " ".join(
            t.get("customer_query", "") for t in test_case.get("turns", [])
        ) or test_case.get("customer_query", "")
        combined_response = " ".join(all_responses)

        instruction_size_tokens = self._estimate_tokens(instruction_size_chars)
        query_tokens = self._estimate_tokens(combined_query)
        response_tokens = self._estimate_tokens(combined_response)
        input_tokens = instruction_size_tokens + query_tokens

        expected_tools = test_case.get("expected_tools", [])
        required_tools = test_case.get("required_tools", [])
        irrelevant_tool_calls_count = self._count_out_of_domain_calls(
            all_tool_names, category, active_skill=detected_domain
        )
        # cross_domain_calls_count: fair comparison across agents — always based on
        # the test's category (not the skill the agent chose to activate). This is
        # the "calls outside the task's intended domain" number.
        expected_domain = _CATEGORY_TO_DOMAIN.get(category)
        expected_allowed = set(_DOMAIN_TOOLS.get(expected_domain, [])) if expected_domain else set()
        cross_domain_calls_count = (
            sum(1 for name in all_tool_names if name not in expected_allowed)
            if expected_allowed else 0
        )
        if required_tools:
            required_hits = sum(
                1 for rt in required_tools
                if any(rt in name or name == rt for name in all_tool_names)
            )
            required_tool_coverage = required_hits / len(required_tools)
            called_required = sum(
                1 for name in all_tool_names
                if any(rt in name for rt in required_tools)
            )
            tool_precision = called_required / max(len(all_tool_names), 1)
        else:
            required_tool_coverage = 1.0
            tool_precision = 1.0

        cost_estimate = self._estimate_cost(input_tokens + tool_schema_tokens, response_tokens)

        return MetricSnapshot(
            test_id=test_case.get("id", "unknown"),
            agent_variant=agent_variant,
            query=combined_query,
            success=success,
            response=combined_response,
            instruction_size_chars=instruction_size_chars,
            instruction_size_tokens=instruction_size_tokens,
            input_tokens=input_tokens,
            query_tokens=query_tokens,
            response_tokens=response_tokens,
            total_request_tokens=query_tokens + response_tokens,
            latency_ms=total_latency_ms,
            tool_calls_count=len(all_tool_names),
            tool_call_names=all_tool_names,
            irrelevant_tool_calls_count=irrelevant_tool_calls_count,
            tools_exposed_count=tools_exposed_count,
            tool_schema_tokens=tool_schema_tokens,
            required_tool_coverage=round(required_tool_coverage, 3),
            cross_domain_calls_count=cross_domain_calls_count,
            grounded_answer=bool(success and required_tool_coverage > 0),
            domain_detected=detected_domain,
            hallucination_detected=self._detect_hallucination(combined_response),
            tool_precision=tool_precision,
            cost_estimate_usd=cost_estimate,
        )

    async def run_agent(self, agent_variant: str, test_case: Dict[str, Any]) -> MetricSnapshot:
        """Run a single-turn test case against one agent variant."""
        agent_class = await self._import_agent_class(agent_variant)
        session_id = f"eval_{agent_variant}_{self.session_counter}_{int(time.time() * 1000)}"
        self.session_counter += 1
        agent = agent_class(self.state_store, session_id)

        query = test_case.get("customer_query", "")
        start_time = time.time()
        try:
            response = await agent.chat_async(query)
            success = True
        except Exception as e:
            logger.error(f"Agent failed on test {test_case.get('id')}: {e}")
            response = f"Error: {str(e)}"
            success = False
        latency_ms = (time.time() - start_time) * 1000

        tool_calls = agent.get_tool_calls() if hasattr(agent, "get_tool_calls") else []
        tool_call_names = [tc.get("name", "unknown") for tc in tool_calls]

        snapshot = self._build_snapshot(
            agent_variant, test_case, agent,
            [response], tool_call_names, latency_ms, success,
        )
        logger.info(f"[{agent_variant.upper()}] {test_case.get('id')}: {latency_ms:.0f}ms, "
                    f"tokens={snapshot.total_request_tokens}, success={success}")
        return snapshot

    async def run_multi_turn_agent(
        self, agent_variant: str, test_case: Dict[str, Any]
    ) -> MetricSnapshot:
        """
        Run a multi-turn test case by sending each turn sequentially
        to the SAME agent instance (preserving thread/session context).
        Metrics are aggregated across all turns.
        """
        agent_class = await self._import_agent_class(agent_variant)
        session_id = f"eval_{agent_variant}_{self.session_counter}_{int(time.time() * 1000)}"
        self.session_counter += 1
        agent = agent_class(self.state_store, session_id)

        turns = test_case.get("turns", [])
        all_responses: List[str] = []
        all_tool_names: List[str] = []
        total_latency_ms = 0.0
        success = True

        for turn_idx, turn in enumerate(turns):
            query = turn.get("customer_query", "")
            turn_num = turn.get("turn_number", turn_idx + 1)
            logger.info(f"  [{agent_variant.upper()}] turn {turn_num}/{len(turns)}: {query[:60]}...")

            start_time = time.time()
            try:
                response = await agent.chat_async(query)
            except Exception as e:
                logger.error(f"Agent failed on turn {turn_num} of {test_case.get('id')}: {e}")
                response = f"Error: {str(e)}"
                success = False
            total_latency_ms += (time.time() - start_time) * 1000

            all_responses.append(response)
            turn_tool_calls = agent.get_tool_calls() if hasattr(agent, "get_tool_calls") else []
            all_tool_names.extend(tc.get("name", "unknown") for tc in turn_tool_calls)

        snapshot = self._build_snapshot(
            agent_variant, test_case, agent,
            all_responses, all_tool_names, total_latency_ms, success,
        )
        logger.info(
            f"[{agent_variant.upper()}] {test_case.get('id')} "
            f"({len(turns)} turns): {total_latency_ms:.0f}ms, "
            f"tokens={snapshot.total_request_tokens}, success={success}"
        )
        return snapshot

    async def evaluate_dataset(
        self,
        dataset_path: str,
        sample_fraction: float = 1.0,
        turn_type: str = "all",  # "single", "multi", or "all"
        repeats: int = 1,
    ) -> List[Dict[str, Any]]:
        """Run evaluation on dataset, filtered by turn type.

        When ``repeats > 1``, each test is executed N times per variant and
        determinism metrics (tool-set Jaccard, tool-order match rate, required-
        coverage stdev, success rate) are computed across the repeats.
        """
        with open(dataset_path, "r") as f:
            data = json.load(f)

        test_cases = data.get("test_cases", [])

        # Filter by turn type
        if turn_type == "single":
            test_cases = [t for t in test_cases if not t.get("multi_turn", False)]
        elif turn_type == "multi":
            test_cases = [t for t in test_cases if t.get("multi_turn", False)]

        total_available = len(test_cases)

        # Apply sampling within the filtered pool
        if sample_fraction < 1.0:
            import random
            sample_size = max(1, int(total_available * sample_fraction))
            test_cases = random.sample(test_cases, sample_size)

        logger.info(
            f"[{turn_type.upper()}] Running {len(test_cases)} / {total_available} test cases"
            + (f" x {repeats} repeats" if repeats > 1 else "")
        )

        results: List[Dict[str, Any]] = []
        for idx, test_case in enumerate(test_cases):
            logger.info(
                f"Evaluating test case {idx + 1}/{len(test_cases)}: {test_case.get('id')}"
            )
            is_multi = test_case.get("multi_turn", False)
            run = self.run_multi_turn_agent if is_multi else self.run_agent

            baseline_runs: List[MetricSnapshot] = []
            skills_runs: List[MetricSnapshot] = []
            for rep in range(repeats):
                if repeats > 1:
                    logger.info(f"  repeat {rep + 1}/{repeats}")
                baseline_runs.append(await run("baseline", test_case))
                await asyncio.sleep(0.5)
                skills_runs.append(await run("skills", test_case))
                await asyncio.sleep(0.5)

            entry: Dict[str, Any] = {
                "test_id": test_case.get("id"),
                "baseline": baseline_runs[0],
                "skills": skills_runs[0],
            }
            if repeats > 1:
                entry["baseline_runs"] = baseline_runs
                entry["skills_runs"] = skills_runs
                entry["determinism"] = {
                    "baseline": _compute_determinism(baseline_runs),
                    "skills": _compute_determinism(skills_runs),
                }
            results.append(entry)

        return results


def print_comparison_table(results: List[Dict[str, MetricSnapshot]], title: str = "BASELINE vs SKILLS-ROUTED") -> Dict[str, Any]:
    """Print side-by-side comparison table and return three headline metrics."""
    
    print("\n" + "=" * 150)
    print(f"AGENT COMPARISON: {title}")
    print("=" * 150)
    
    # Header
    print(f"{'Test ID':<25} {'Metric':<30} {'Baseline':<30} {'Skills':<30} {'Delta':<20}")
    print("-" * 150)
    
    totals_baseline = {
        "latency_ms": 0,
        "instruction_tokens": 0,
        "input_tokens": 0,
        "total_tokens": 0,
        "cost": 0,
        "success_count": 0,
        "irrelevant_tool_calls": 0,
    }
    totals_skills = dict(totals_baseline)
    
    for row in results:
        test_id = row["test_id"]
        baseline = row["baseline"]
        skills = row["skills"]
        
        # Latency comparison
        latency_delta = skills.latency_ms - baseline.latency_ms
        latency_pct = (latency_delta / baseline.latency_ms * 100) if baseline.latency_ms > 0 else 0
        print(f"{test_id:<25} {'Latency (ms)':<30} {baseline.latency_ms:<30.1f} {skills.latency_ms:<30.1f} {latency_pct:>+6.1f}%")
        
        # Token usage comparison
        tokens_delta = skills.total_request_tokens - baseline.total_request_tokens
        tokens_pct = (tokens_delta / baseline.total_request_tokens * 100) if baseline.total_request_tokens > 0 else 0
        print(f"{'':<25} {'Total Tokens':<30} {baseline.total_request_tokens:<30} {skills.total_request_tokens:<30} {tokens_pct:>+6.1f}%")
        
        # Context (instruction) size
        context_delta = skills.instruction_size_tokens - baseline.instruction_size_tokens
        context_pct = (context_delta / baseline.instruction_size_tokens * 100) if baseline.instruction_size_tokens > 0 else 0
        print(f"{'':<25} {'Instruction Tokens':<30} {baseline.instruction_size_tokens:<30} {skills.instruction_size_tokens:<30} {context_pct:>+6.1f}%")
        
        # Cost comparison
        cost_delta = skills.cost_estimate_usd - baseline.cost_estimate_usd
        cost_pct = (cost_delta / baseline.cost_estimate_usd * 100) if baseline.cost_estimate_usd > 0 else 0
        print(f"{'':<25} {'Est. Cost ($)':<30} {baseline.cost_estimate_usd:<30.6f} {skills.cost_estimate_usd:<30.6f} {cost_pct:>+6.1f}%")
        
        # Tool call accuracy
        precision_delta = skills.tool_precision - baseline.tool_precision
        print(f"{'':<25} {'Tool Precision':<30} {baseline.tool_precision:<30.2f} {skills.tool_precision:<30.2f} {precision_delta:>+7.2f}")

        # Cross-domain tool calls (calls to a different skill domain)
        irrelevant_delta = skills.irrelevant_tool_calls_count - baseline.irrelevant_tool_calls_count
        print(
            f"{'':<25} {'Cross-Domain Calls':<30} "
            f"{baseline.irrelevant_tool_calls_count:<30} "
            f"{skills.irrelevant_tool_calls_count:<30} "
            f"{irrelevant_delta:>+7d}"
        )
        
        # Success rate
        baseline_success = "OK" if baseline.success else "FAIL"
        skills_success = "OK" if skills.success else "FAIL"
        print(f"{'':<25} {'Success':<30} {baseline_success:<30} {skills_success:<30}")
        
        # Domain detection (skills only)
        if skills.domain_detected:
            print(f"{'':<25} {'Domain Detected':<30} {'-':<30} {skills.domain_detected:<30}")
        
        print("-" * 150)
        
        # Accumulate totals
        totals_baseline["latency_ms"] += baseline.latency_ms
        totals_baseline["instruction_tokens"] += baseline.instruction_size_tokens
        totals_baseline["input_tokens"] += baseline.input_tokens
        totals_baseline["total_tokens"] += baseline.total_request_tokens
        totals_baseline["cost"] += baseline.cost_estimate_usd
        totals_baseline["success_count"] += 1 if baseline.success else 0
        totals_baseline["irrelevant_tool_calls"] += baseline.irrelevant_tool_calls_count
        
        totals_skills["latency_ms"] += skills.latency_ms
        totals_skills["instruction_tokens"] += skills.instruction_size_tokens
        totals_skills["input_tokens"] += skills.input_tokens
        totals_skills["total_tokens"] += skills.total_request_tokens
        totals_skills["cost"] += skills.cost_estimate_usd
        totals_skills["success_count"] += 1 if skills.success else 0
        totals_skills["irrelevant_tool_calls"] += skills.irrelevant_tool_calls_count
    
    # Totals and averages
    num_tests = len(results)
    if num_tests > 0:
        print("SUMMARY (Totals / Averages)")
        print("-" * 150)
        
        avg_latency_baseline = totals_baseline["latency_ms"] / num_tests
        avg_latency_skills = totals_skills["latency_ms"] / num_tests
        latency_delta = avg_latency_skills - avg_latency_baseline
        latency_pct = (latency_delta / avg_latency_baseline * 100) if avg_latency_baseline > 0 else 0
        print(f"{'AVERAGE':<25} {'Latency (ms)':<30} {avg_latency_baseline:<30.1f} {avg_latency_skills:<30.1f} {latency_pct:>+6.1f}%")
        
        avg_input_baseline = totals_baseline["input_tokens"] / num_tests
        avg_input_skills = totals_skills["input_tokens"] / num_tests
        input_delta = avg_input_skills - avg_input_baseline
        input_pct = (input_delta / avg_input_baseline * 100) if avg_input_baseline > 0 else 0
        print(f"{'AVERAGE':<25} {'Input Tokens':<30} {avg_input_baseline:<30.1f} {avg_input_skills:<30.1f} {input_pct:>+6.1f}%")

        avg_tokens_baseline = totals_baseline["total_tokens"] / num_tests
        avg_tokens_skills = totals_skills["total_tokens"] / num_tests
        tokens_delta = avg_tokens_skills - avg_tokens_baseline
        tokens_pct = (tokens_delta / avg_tokens_baseline * 100) if avg_tokens_baseline > 0 else 0
        print(f"{'AVERAGE':<25} {'Total Tokens':<30} {avg_tokens_baseline:<30.1f} {avg_tokens_skills:<30.1f} {tokens_pct:>+6.1f}%")

        print(
            f"{'TOTAL':<25} {'Cross-Domain Calls':<30} "
            f"{totals_baseline['irrelevant_tool_calls']:<30} "
            f"{totals_skills['irrelevant_tool_calls']:<30}"
        )
        
        print(f"{'TOTAL':<25} {'Cost ($)':<30} {totals_baseline['cost']:<30.6f} {totals_skills['cost']:<30.6f}")
        print(f"{'TOTAL':<25} {'Success Rate':<30} {totals_baseline['success_count']}/{num_tests} {totals_skills['success_count']}/{num_tests}")
    
    print("=" * 150 + "\n")

    if not results:
        return {
            "avg_input_tokens_delta_pct": 0.0,
            "irrelevant_tool_calls_delta": 0,
            "success_rate_delta_pct": 0.0,
        }

    # Headline metrics requested by user
    avg_input_baseline = totals_baseline["input_tokens"] / len(results)
    avg_input_skills = totals_skills["input_tokens"] / len(results)
    avg_input_tokens_delta_pct = (
        ((avg_input_skills - avg_input_baseline) / avg_input_baseline) * 100
        if avg_input_baseline > 0
        else 0.0
    )

    irrelevant_tool_calls_delta = totals_skills["irrelevant_tool_calls"] - totals_baseline["irrelevant_tool_calls"]

    baseline_success_rate = (totals_baseline["success_count"] / len(results)) * 100
    skills_success_rate = (totals_skills["success_count"] / len(results)) * 100
    success_rate_delta_pct = skills_success_rate - baseline_success_rate

    headline = {
        "avg_input_tokens_delta_pct": round(avg_input_tokens_delta_pct, 2),
        "irrelevant_tool_calls_delta": irrelevant_tool_calls_delta,
        "success_rate_delta_pct": round(success_rate_delta_pct, 2),
    }

    print("HEADLINE METRICS")
    print("-" * 150)
    print(f"Input Token Delta (%): {headline['avg_input_tokens_delta_pct']:+.2f}%")
    print(f"Irrelevant Tool-Call Delta: {headline['irrelevant_tool_calls_delta']:+d}")
    print(f"Success-Rate Delta (% points): {headline['success_rate_delta_pct']:+.2f}")
    print("=" * 150 + "\n")

    return headline


async def main():
    parser = argparse.ArgumentParser(description="A/B test single agent vs skills-routed agent")
    parser.add_argument("--baseline", default="agents.agent_framework.single_agent",
                        help="Baseline agent module path")
    parser.add_argument("--variant", default="agents.agent_framework.single_agent_skills",
                        help="Variant agent module path")
    parser.add_argument("--dataset", default="agentic_ai/evaluations/eval_dataset.json",
                        help="Path to eval dataset")
    parser.add_argument("--sample", type=float, default=1.0,
                        help="Fraction of SINGLE-TURN cases to sample (0-1). Multi-turn always runs all.")
    parser.add_argument("--turn-type", default="all", choices=["all", "single", "multi"],
                        help="Which turn types to evaluate: all (default), single, or multi.")
    parser.add_argument("--repeats", type=int, default=1,
                        help="Number of times to repeat each test per variant. >1 enables determinism metrics.")
    parser.add_argument("--output", default="eval_results/comparison_skills.json",
                        help="Base output file path. Suffixed with _single / _multi automatically.")

    args = parser.parse_args()

    if not Path(args.dataset).exists():
        logger.error(f"Dataset not found: {args.dataset}")
        sys.exit(1)

    evaluator = AgentEvaluator(args.baseline, args.variant)
    output_base = Path(args.output).with_suffix("")
    all_results = {}

    # ── Single-turn ───────────────────────────────────────────────────────────
    if args.turn_type in ("all", "single"):
        print("\n" + "#" * 150)
        print(f"# SINGLE-TURN EVALUATION  (sample={args.sample:.0%} of 25 single-turn cases)")
        print("#" * 150)
        single_results = await evaluator.evaluate_dataset(
            args.dataset, sample_fraction=args.sample, turn_type="single",
            repeats=args.repeats,
        )
        single_headline = print_comparison_table(single_results, title="SINGLE-TURN: BASELINE vs SKILLS")
        all_results["single_turn"] = {
            "headline": single_headline,
            "num_tests": len(single_results),
            "repeats": args.repeats,
            "results": [_serialize_entry(r) for r in single_results],
        }

    # ── Multi-turn ────────────────────────────────────────────────────────────
    if args.turn_type in ("all", "multi"):
        print("\n" + "#" * 150)
        print("# MULTI-TURN EVALUATION  (all 5 multi-turn cases, full conversation per case)")
        print("#" * 150)
        multi_results = await evaluator.evaluate_dataset(
            args.dataset, sample_fraction=1.0, turn_type="multi",
            repeats=args.repeats,
        )
        multi_headline = print_comparison_table(multi_results, title="MULTI-TURN: BASELINE vs SKILLS")
        all_results["multi_turn"] = {
            "headline": multi_headline,
            "num_tests": len(multi_results),
            "repeats": args.repeats,
            "results": [_serialize_entry(r) for r in multi_results],
        }

    # ── Combined headline summary ─────────────────────────────────────────────
    print("\n" + "=" * 150)
    print("COMBINED HEADLINE SUMMARY")
    print("=" * 150)
    for group, data in all_results.items():
        h = data["headline"]
        print(f"  {group.replace('_', '-').upper()} ({data['num_tests']} tests):")
        print(f"    Input Token Delta:    {h['avg_input_tokens_delta_pct']:+.2f}%")
        print(f"    Cross-Domain Delta:   {h['irrelevant_tool_calls_delta']:+d} calls")
        print(f"    Success-Rate Delta:   {h['success_rate_delta_pct']:+.2f} pp")
    print("=" * 150)

    # ── Save results ──────────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "baseline_module": args.baseline,
            "variant_module": args.variant,
            **all_results,
        }, f, indent=2)
    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
