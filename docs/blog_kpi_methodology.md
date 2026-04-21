# KPI Methodology — How every metric in the blog is measured

This doc lists **only** the KPIs that appear in the blog's 30-test Pair A and Pair B result tables, with the exact formula, data source, and any caveats.

**Source of truth:** [`agentic_ai/evaluations/compare_agents_skills.py`](../agentic_ai/evaluations/compare_agents_skills.py) — specifically `MetricSnapshot` and `_build_snapshot`.

**Experimental setup:**
- Dataset: [`agentic_ai/evaluations/eval_dataset.json`](../agentic_ai/evaluations/eval_dataset.json), 30 cases (25 single-turn + 5 multi-turn).
- Model: `gpt-5.4-nano` on Azure OpenAI, same temperature and system-prompt strategy across agents.
- MCP server: single instance at `http://localhost:8000/mcp`, 18 tools spanning billing, security, product, and ticket domains.
- Pair A (context tax): `single_agent` vs `single_agent_skills`, 30 tests × **1 repeat**.
- Pair B (drift / determinism): `reflection_agent` vs `reflection_workflow_agent`, 30 tests × **3 repeats**.
- Pricing: Azure OpenAI GPT-4-class rates (see §3).

Aggregation code: [`agentic_ai/evaluations/_story_30.py`](../agentic_ai/evaluations/_story_30.py).

---

## 1. Context-size KPIs

These describe what the model "sees" on every turn. They are the core of **Tax #1 (context bloat)**.

| KPI | Formula / source |
|---|---|
| `instruction_size_chars` | Baseline: hard-coded 2000 chars. Skills: `skill_info["instruction_chars"]` reported by the routed skill card. |
| `instruction_size_tokens` | `max(1, instruction_size_chars // 4)` (~4 chars per token). |
| `tools_exposed_count` | Baseline: `_BASELINE_TOOL_COUNT = 18`. Skills: `len(skill_info["allowed_tools"])`. |
| `tool_schema_tokens` | `tools_exposed_count × _TOKENS_PER_TOOL_SCHEMA` where `_TOKENS_PER_TOOL_SCHEMA = 80`. **Caveat:** this is a *modeled* estimate, not tokens measured off the wire. 80 is a reasonable average across our MCP catalogue, but individual schemas range roughly 40–150 tokens depending on argument complexity. Treat per-turn values as ±25% estimates; aggregate deltas are accurate because both sides of each comparison use the same constant. |
| `tools_exposed_count` distribution | Reported as per-turn integers in the raw JSON. When the blog/table shows a decimal (e.g. mean 6.64), that is the **cross-test mean** of those integers — the actual per-turn count is always a whole number. |
| `input_tokens` | `instruction_size_tokens + query_tokens`, where `query_tokens = max(1, len(combined_query) // 4)` and `combined_query` is the space-joined concatenation of every turn's `customer_query`. **Does not include `tool_schema_tokens`** — those are accounted for separately in the cost formula. |
| `response_tokens` | `max(1, len(combined_response) // 4)`, with `combined_response` being the space-joined concatenation of every turn's final response. |

---

## 2. Latency KPIs

| KPI | Formula / source |
|---|---|
| `latency_ms` | Wall-clock `end − start` around the full agent invocation (includes any internal classifier hop, tool calls, reflection, refinement). Measured in the harness, not in the agent. |
| `latency_stdev_ms` (section-level) | Population standard deviation of `latency_ms` over the flattened per-run values within a section (e.g. for Pair B single-turn: 25 tests × 3 repeats = 75 latencies). Only meaningful with `--repeats > 1`; for Pair A (1 repeat) it's stdev across tests. |

---

## 3. Cost KPI

```
cost_estimate_usd
  = ((input_tokens + tool_schema_tokens) / 1000) × 0.003
  +   (response_tokens                   / 1000) × 0.006
```

Pricing constants (hard-coded in `AgentEvaluator.PRICING`):

| | USD per 1K tokens |
|---|---:|
| Input | 0.003 |
| Output | 0.006 |

Cost explicitly includes `tool_schema_tokens` because the chat-completion API charges for the serialized tool schema. Using `input_tokens` alone would understate cost.

---

## 4. Success KPI

| KPI | Formula / source |
|---|---|
| `success` (per-test) | Boolean returned by the agent loop: `True` iff the agent produced a non-empty final response without raising. |
| `success_rate` (section-level) | `passes / total_tests` for Pair A (1 repeat); `passes / (tests × repeats)` flattened for Pair B. |

This is a **liveness** signal, not a rubric score. The blog frames quality conservatively because of this — the claim is "quality preserved / not regressed," not "quality improved." A stronger future harness would route `(query, response, success_criteria, scoring_rubric)` through an LLM judge.

---

## 5. Section aggregation (how the blog's tables are built)

Each output JSON contains a `single_turn` and a `multi_turn` section. Within each:

- **Per-test averages** are arithmetic means across the tests in that section.
- For Pair B (`--repeats 3`), each test's reported value is first averaged across its 3 repeats; the section mean is then the mean of those per-test means.
- **`latency_stdev_ms`** is population stdev over the fully flattened run list (not mean of per-test stdevs).
- **Totals** (e.g. "Total input tokens" in the full-story script) are sums across tests, using each test's averaged-across-repeats value.

---

## 6. Constants used throughout

```python
_TOKENS_PER_TOOL_SCHEMA = 80     # empirical per-tool schema tax
_BASELINE_TOOL_COUNT    = 18     # full MCP catalogue at time of runs

PRICING = {
    "input_per_1k_tokens":  0.003,
    "output_per_1k_tokens": 0.006,
}
```

Changing any of these will change the numbers — pin them in the write-up if you reproduce.

---

## 7. What this harness does *not* measure (explicitly out of scope for the blog)

- **No LLM-judge scoring of response quality against `success_criteria`.** `success` is a liveness signal.
- **No API-reported token counts.** Tokens are estimated from character counts (`chars // 4`). If exact cost is critical, swap in `usage.total_tokens` from the chat-completion response.
- **Tool-level KPIs** (`tool_calls_count`, `required_tool_coverage`, `irrelevant_tool_calls_count`, `cross_domain_calls_count`, `tool_precision`, `tool_set_jaccard`, `tool_order_match_rate`, `grounded_answer`, `hallucination_detected`) are computed by the harness but **deliberately excluded from the blog tables** — at the time of the 30-test runs the tool-tracking mixin was not wired on every baseline agent, so those numbers are not trustworthy for a baseline-vs-variant comparison. The blog's determinism story uses `latency_stdev_ms` and `success_rate`, both of which are independent of tool tracking.
