# Agent Experiments — Skills & Workflow Comparison

Companion guide for the blog post *"Two taxes your MCP agent is paying."* Run each agent variant on your own MCP server, reproduce the blog's numbers, or swap in your own dataset.

> **Not to be confused with [`README.md`](./README.md)**, which covers the Azure AI Foundry evaluation pipeline. This file covers the local A/B comparison harness (`compare_agents_skills.py`) only.

---

## Table of contents

1. [What these experiments compare](#1-what-these-experiments-compare)
2. [Prerequisites](#2-prerequisites)
3. [The four agent variants](#3-the-four-agent-variants)
4. [Experiment 1 — Skills only (single agent)](#4-experiment-1--skills-only-single-agent)
5. [Experiment 2 — Skills + workflow (reflection agent)](#5-experiment-2--skills--workflow-reflection-agent)
6. [Interpreting the output JSON](#6-interpreting-the-output-json)
7. [KPI reference](#7-kpi-reference)
8. [Using your own dataset](#8-using-your-own-dataset)

---

## 1. What these experiments compare

Two independent A/B pairs, each isolating one variable:

| Experiment | Baseline | Variant | Variable isolated |
|---|---|---|---|
| **Experiment 1** | `single_agent` | `single_agent_skills` | Skills routing (no workflow on either side) |
| **Experiment 2** | `reflection_agent` | `reflection_workflow_agent` | Skills routing + declarative workflow (both on) |

Both experiments use the same 30-case dataset ([`eval_dataset.json`](./eval_dataset.json)) split into 25 single-turn + 5 multi-turn cases across billing / security / product / ticket domains.

---

## 2. Prerequisites

- Azure OpenAI deployment (any chat model)
- Python 3.12 + `uv` (or `pip`)
- API key, or `az login` for managed identity

### One-time setup

```powershell
git clone https://github.com/microsoft/OpenAIWorkshop
cd OpenAIWorkshop

# MCP server deps
cd mcp
uv sync

# Agent + eval deps
cd ..\agentic_ai\applications
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure `.env` (at repo root)

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_VERSION=2024-12-01-preview
# Either:
AZURE_OPENAI_API_KEY=<key>
# Or rely on managed identity — just run `az login`
MCP_SERVER_URI=http://localhost:8000/mcp
```

### Start the MCP server (leave running)

```powershell
cd mcp
uv run python mcp_service.py
# Listens on http://localhost:8000/mcp
```

---

## 3. The four agent variants

| # | Module | File | What it does |
|---|---|---|---|
| 1 | `agents.agent_framework.single_agent` | [`single_agent.py`](../agents/agent_framework/single_agent.py) | Baseline: one LLM, one system prompt, **all 18 MCP tools** visible every turn. |
| 2 | `agents.agent_framework.single_agent_skills` | [`single_agent_skills.py`](../agents/agent_framework/single_agent_skills.py) | Adds a lightweight domain classifier. Each turn loads one skill card ([`skills.py`](../agents/agent_framework/skills.py)) + only that domain's ~5 tools. |
| 3 | `agents.agent_framework.multi_agent.reflection_agent` | [`reflection_agent.py`](../agents/agent_framework/multi_agent/reflection_agent.py) | Primary → Reviewer → Primary refine loop. Imperative orchestration, full tool catalogue on every call. |
| 4 | `agents.agent_framework.multi_agent.reflection_workflow_agent` | [`reflection_workflow_agent.py`](../agents/agent_framework/multi_agent/reflection_workflow_agent.py) | Same three roles, but orchestrated as a declarative workflow graph with typed state, and each node is skills-routed. |

---

## 4. Experiment 1 — Skills only (single agent)

**Goal:** measure what skills routing alone does (context, cost, latency, variance) with no workflow on either side.

```powershell
cd agentic_ai
.\applications\.venv\Scripts\python.exe .\evaluations\compare_agents_skills.py `
  --baseline agents.agent_framework.single_agent `
  --variant  agents.agent_framework.single_agent_skills `
  --dataset  .\evaluations\eval_dataset.json `
  --output   .\evaluations\eval_results\comparison_single_full.json
```

- Runtime: ~10–15 minutes (30 tests × 2 agents × 1 repeat).
- Output: `evaluations/eval_results/comparison_single_full.json`.

**What to look for:** context-size and cost deltas should move in lockstep across single-turn and multi-turn (roughly −60% `tool_schema_tokens`, ~30–50% `cost_estimate_usd`). Latency should stay flat. Variance (`latency_stdev_ms`) should collapse on multi-turn only.

---

## 5. Experiment 2 — Skills + workflow (reflection agent)

**Goal:** measure what a declarative workflow graph adds on top of skills, specifically for multi-turn / multi-role coordination. `--repeats 3` is essential — the whole point is measuring latency variance.

```powershell
.\applications\.venv\Scripts\python.exe .\evaluations\compare_agents_skills.py `
  --baseline agents.agent_framework.multi_agent.reflection_agent `
  --variant  agents.agent_framework.multi_agent.reflection_workflow_agent `
  --dataset  .\evaluations\eval_dataset.json `
  --repeats  3 `
  --output   .\evaluations\eval_results\comparison_reflection_determinism.json
```

- Runtime: ~60–90 minutes (30 tests × 2 agents × 3 repeats).
- Output: `evaluations/eval_results/comparison_reflection_determinism.json`.

**What to look for:** single-turn will show a small latency tax (workflow overhead with nothing to orchestrate). Multi-turn is where the graph earns its keep — expect a large drop in `latency_stdev_ms` (variance collapse) and a meaningful drop in `latency_ms` (mean).

---

## 6. Interpreting the output JSON

Each run produces a single JSON with this top-level shape:

```json
{
  "baseline_agent": "agents.agent_framework.single_agent",
  "variant_agent":  "agents.agent_framework.single_agent_skills",
  "num_tests": 30,
  "repeats": 1,
  "single_turn": {
    "num_tests": 25,
    "baseline_avg": { "input_tokens": 523, "cost_estimate_usd": 0.00686, "latency_ms": 9075, "...": "..." },
    "variant_avg":  { "input_tokens": 217, "cost_estimate_usd": 0.00337, "latency_ms": 9792, "...": "..." },
    "headline":     { "input_token_delta_pct": -58.5, "cost_delta_pct": -50.8, "latency_delta_pct": 7.9, "...": "..." }
  },
  "multi_turn": { "...": "..." },
  "per_test": [ { "test_id": "...", "baseline": { "...": "..." }, "variant": { "...": "..." } } ]
}
```

- **`per_test`** — raw snapshots (one entry per test, or per test × repeat for Experiment 2). Preserved so you can recompute any metric.
- **`single_turn` / `multi_turn`** — section summaries with averages and deltas.
- **`headline`** — the five-to-seven deltas the blog quotes.

---

## 7. KPI reference

The harness computes these nine KPIs for every test. Source: [`compare_agents_skills.py`](./compare_agents_skills.py) (`MetricSnapshot` and `_build_snapshot`).

### Context (per turn)

| KPI | Formula / source |
|---|---|
| `instruction_size_tokens` | `max(1, instruction_size_chars // 4)`. Baseline uses a hard-coded 2000-char system prompt; skills variants use the routed skill card's length. |
| `tools_exposed_count` | Baseline = 18 (full catalogue). Skills variants = `len(skill_info["allowed_tools"])`, typically 5–9. Reported as whole numbers per turn; cross-test means may be decimal. |
| `tool_schema_tokens` | `tools_exposed_count × 80`. **Modeled, not wire-measured** — individual schemas range 40–150 tokens. Aggregate deltas are accurate because both sides use the same constant. |
| `input_tokens` | `instruction_size_tokens + query_tokens` where `query_tokens = max(1, len(combined_query) // 4)`. Does **not** include `tool_schema_tokens`. |
| `response_tokens` | `max(1, len(combined_response) // 4)`. |

### Latency

| KPI | Formula / source |
|---|---|
| `latency_ms` | Wall-clock `end − start` around the full agent invocation. Includes classifier hop, tool calls, reflection, refinement. |
| `latency_stdev_ms` | Population standard deviation of `latency_ms` across the flattened per-run values within a section. Only meaningful with `--repeats > 1`. |

### Cost

```
cost_estimate_usd
  = ((input_tokens + tool_schema_tokens) / 1000) × 0.003
  +   (response_tokens                   / 1000) × 0.006
```

Input and output pricing are hard-coded in `AgentEvaluator.PRICING`. Cost **includes** `tool_schema_tokens` because the chat-completion API charges for the serialized tool schema.

### Success

| KPI | Meaning |
|---|---|
| `success` / `success_rate` | Liveness signal: `True` iff the agent produced a non-empty final response without raising. **Not a quality rubric.** A stronger harness would route `(query, response, success_criteria, scoring_rubric)` through an LLM judge. |

### Constants

```python
_TOKENS_PER_TOOL_SCHEMA = 80     # empirical per-tool schema tax
_BASELINE_TOOL_COUNT    = 18     # full MCP catalogue

PRICING = {
    "input_per_1k_tokens":  0.003,
    "output_per_1k_tokens": 0.006,
}
```

Changing any of these changes the numbers — pin them in write-ups.

### What the harness does *not* measure

- No LLM-judge scoring of response quality against `success_criteria`.
- No API-reported token counts (tokens are estimated from `chars // 4`; swap in `usage.total_tokens` if exact cost matters).
- Tool-level KPIs (`tool_calls_count`, `tool_precision`, etc.) are computed but deliberately excluded from the blog tables — the tool-tracking mixin wasn't wired on every baseline at the time of the published runs.

---

## 8. Using your own dataset

`eval_dataset.json` is a JSON array of test cases with this shape:

```json
{
  "test_id": "billing_unknown_charge",
  "customer_id": 1,
  "customer_query": "There's a $47 charge I don't recognize on my bill...",
  "expected_tools": ["get_customer_detail", "get_invoice_payments"],
  "required_tools": ["get_invoice_payments"],
  "success_criteria": "...",
  "ground_truth_solution": "...",
  "scoring_rubric": "..."
}
```

Multi-turn cases use a list for `customer_query`. Replace the file and re-run either experiment — same harness, your numbers.
