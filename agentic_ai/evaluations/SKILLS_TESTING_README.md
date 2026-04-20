# Skills-Based Agent Testing Guide

This directory demonstrates the **skills concept** for reducing context bloat and improving agent precision through domain-specific instruction loading.

## What We Built

### 1. Domain Skills (`.github/skills/`)

Three focused, reusable skill files, each with domain-specific instructions:
- `contoso-billing-skill/SKILL.md` — Billing, CRM, payments, subscriptions
- `contoso-product-skill/SKILL.md` — Product catalog, promotions, features
- `contoso-security-skill/SKILL.md` — Security, authentication, lockouts

Each skill:
- Defines clear tool sets and boundaries
- Avoids generic "be helpful" instructions
- Includes explicit domain fallback rules
- ~500–800 tokens each (vs generic ~2000 token baseline)

### 2. Skill-Routed Agent (`single_agent_skills.py`)

A variant of the baseline single agent that:
1. **Detects domain** from user query (lightweight keyword matching)
2. **Loads only the relevant skill** instructions
3. **Uses focused context** instead of all-knowing prompt
4. **Tracks domain confidence** for telemetry

### 3. A/B Evaluation (`compare_agents_skills.py`)

Comprehensive tester that:
- Runs both baseline and skills agents on identical test set
- Measures:
  - **Context size** (instruction token reduction)
  - **Token usage** (input + output)
  - **Latency** (time-to-first-token, total)
  - **Accuracy & tool precision**
  - **Cost estimate** ($ per request)
  - **Hallucination detection**
- Outputs side-by-side table + JSON details

---

## Running the Test

### Prerequisites

1. **MCP server running** (port 8000)
   ```bash
   cd mcp
   uv run python mcp_service.py
   ```

2. **Environment configured** (`.env`)
   ```bash
   AZURE_OPENAI_API_KEY=...
   AZURE_OPENAI_ENDPOINT=...
   AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   MCP_SERVER_URI=http://localhost:8000/mcp
   ```

### Quick Test (5 scenarios)

```bash
cd agentic_ai/evaluations

python compare_agents_skills.py \
  --baseline agents.agent_framework.single_agent \
  --variant agents.agent_framework.single_agent_skills \
  --dataset eval_dataset.json \
  --sample 0.15 \
  --output eval_results/comparison_quick.json
```

### Full Evaluation (30 scenarios)

```bash
python compare_agents_skills.py \
  --baseline agents.agent_framework.single_agent \
  --variant agents.agent_framework.single_agent_skills \
  --dataset eval_dataset.json \
  --sample 1.0 \
  --output eval_results/comparison_full.json
```

---

## Expected Results

### Context Size ✓ (Reduction)
- **Baseline**: ~2000 instruction tokens (generic)
- **Skills**: ~500–800 instruction tokens (domain-specific)
- **Savings**: 60–75% context per request

### Latency ≈ (Minimal Change)
- Slight overhead: +10–20ms for domain detection
- Typically offsets due to faster inference with focused context
- **Net: Similar or slightly faster**

### Accuracy ✓ (Improvement)
- Skills agents less likely to hallucinate cross-domain
- Better tool precision (fewer unnecessary calls)
- Domain fallback rules prevent confusion
- **Measure: Hallucination rate, tool precision scores**

### Cost ✓ (Reduction)
- Smaller prompt = fewer input tokens
- Fewer tool calls = less back-and-forth
- **Estimate: 10–20% cost savings at scale**

---

## Understanding the Output

```
==================================================
Test ID         Metric              Baseline    Skills     Delta
==================================================
billing_001     Latency (ms)        1245.5      1198.2     -3.8%
                Total Tokens        1840        1620       -12.0%
                Instruction Tokens  2000        750        -62.5%
                Cost ($)            0.009850    0.008640   -12.2%
                Tool Precision      0.95        0.98       +0.03
                Success             ✓           ✓
                Domain Detected     -           billing
==================================================

SUMMARY
Average Latency:  1150ms → 1130ms (-1.7%)
Average Tokens:   1850 → 1630 (-11.8%)
Total Cost:       $2.95 → $2.61 (-11.5%)
Success Rate:     30/30 → 30/30 (100%)
```

---

## Next Steps: Handoff Pattern

Once you've validated this on single-agent:

1. **Apply skills to handoff multi-domain agent**
   - Each specialist (billing, product, security) loads its own skill
   - Orchestrator stays generic (just routing logic)
   - **Amplified effect**: Each specialist operates in its native domain

2. **Create a `handoff_multi_domain_agent_skills.py`**
   - Reuse domain detection
   - Pass right specialist + right skill to each
   - Track domain switches

3. **Run updated eval**
   ```bash
   python compare_agents_skills.py \
     --baseline agents.agent_framework.multi_agent.handoff_multi_domain_agent \
     --variant agents.agent_framework.multi_agent.handoff_multi_domain_agent_skills
   ```

---

## Architecture Diagram

```
User Query
    ↓
┌─────────────────────────────┐
│ Domain Detector             │
│ (keyword match)             │
└─────────────────────────────┘
        ↓
   ╔═══════════╗
   ║ billing   ║  (Load contoso-billing-skill/SKILL.md)
   ║ product   ║  (Load contoso-product-skill/SKILL.md)
   ║ security  ║  (Load contoso-security-skill/SKILL.md)
   ╚═══════════╝
        ↓
    ┌──────────┐
    │  Agent   │ (With focused instructions + tools)
    └──────────┘
        ↓
    Response (Reduced hallucination, better tool use)
```

---

## Key Metrics to Monitor

| Metric | Baseline Target | Skills Target | Why It Matters |
|--------|----------|-----------|-----------------|
| Instruction Tokens | 2000 | <800 | Reduces context window usage |
| Total Tokens/Request | 1850 | <1700 | Lowers cost at scale |
| Latency (ms) | 1000–1500 | <1500 | User experience |
| Hallucination Rate | 5–10% | <2% | Reliability & trust |
| Tool Precision | 0.90 | >0.95 | Efficiency & correctness |
| Cost per Request | baseline | -10–15% | Operational cost |

---

## Debugging

### Domain Detection Not Working?
Check `single_agent_skills.py` `DomainDetector.DOMAINS` keywords. Add more if needed.

### Skill File Not Loading?
Verify path: `.github/skills/<domain>-skill/SKILL.md`

### Agent Errors?
Check MCP server is running and `MCP_SERVER_URI` is correct.

### Missing Metrics?
Ensure eval dataset has `expected_tools` and `required_tools` fields.

---

## References

- Skills concept: `.github/skills/`
- Agent implementation: `agentic_ai/agents/agent_framework/single_agent_skills.py`
- Evaluator: `agentic_ai/evaluations/compare_agents_skills.py`
- Baseline comparison: See `single_agent.py` and `handoff_multi_domain_agent.py`
