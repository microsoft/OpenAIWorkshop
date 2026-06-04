# MLADS Agent Evaluation — Lab Instructions

> **Session:** From Prototype to Production — Using Rigorous Evaluation to De-Risk AI Agent Investments
> **Date:** 06/10/2026 · 08:00–09:15 PDT · B7 Room 1.2F Fern
> **Repo:** https://github.com/microsoft/OpenAIWorkshop

This single page is everything you need to reproduce the demos shown in the
slides. The longer methodology guide lives at
[`agentic_ai/evaluations/README.md`](../../agentic_ai/evaluations/README.md).

---

## 0 · 60-second tour

| You will run | What it shows |
|---|---|
| `compare_agents.py` against the committed baselines | Slide 15: Single Agent vs Handoff |
| `run_agent_eval.py --agent single --limit 2` | Slide 18: multi-grader scoring of one case in <2 min |
| `run_agent_eval.py --agent single --local` (30 cases) | Slide 20: full baseline (~10 min) |
| `run_agent_eval.py --agent single --remote` | Slide 19: results appear in Azure AI Foundry portal |

---

## 1 · Prerequisites (one-time, ~10 min)

```bash
# Clone & install (Python 3.10+, uv)
git clone https://github.com/microsoft/OpenAIWorkshop.git
cd OpenAIWorkshop
uv sync                                     # root deps
cd agentic_ai/applications && uv sync       # backend deps
cd ../../mcp && uv sync                     # MCP server deps
cd ..

# Azure login (needed for Foundry remote eval)
az login
```

### `.env` file

Copy `agentic_ai/applications/.env.sample` → `agentic_ai/applications/.env`
and fill in **at minimum**:

```bash
AZURE_OPENAI_ENDPOINT="https://<your-aoai>.openai.azure.com"
AZURE_OPENAI_API_KEY="<key>"
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4.1"          # or gpt-5.2
AZURE_OPENAI_API_VERSION="2024-12-01-preview"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small"

# Required for `--remote` (Foundry portal results)
AZURE_AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
AZURE_OPENAI_EVAL_DEPLOYMENT="gpt-5.2"           # judge model

# Local dev convenience
MCP_SERVER_URI="http://localhost:8000/mcp"
BACKEND_URL="http://localhost:7000"
DISABLE_AUTH="true"

# All four agent variants the lab uses
AGENT_MODULES="agents.agent_framework.single_agent,agents.agent_framework.multi_agent.reflection_agent,agents.agent_framework.multi_agent.handoff_multi_domain_agent,agents.agent_framework.multi_agent.magentic_group"
```

### One-time Azure role for Foundry (skip if using local only)

```bash
az role assignment create \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --role "Azure AI Developer" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<ai-project>
```

---

## 2 · Start services (two terminals, keep both open)

**Terminal A — MCP server (18 tools, port 8000)**

```bash
cd mcp
uv run python mcp_service.py
# wait for: "Uvicorn running on http://0.0.0.0:8000"
```

**Terminal B — Agent backend (port 7000)**

```bash
cd agentic_ai/applications
uv run uvicorn backend:app --port 7000 --reload
# wait for: "Application startup complete"
```

**Sanity check (Terminal C):**

```bash
curl http://localhost:8000/health    # MCP
curl http://localhost:7000/auth/config   # backend
```

---

## 3 · Demo 1 — One test case, multi-grader scoring (slides 12, 18) · ~2 min

```bash
cd agentic_ai/applications
uv run python ../evaluations/run_agent_eval.py --agent single --limit 2 --local
```

You'll see each metric scored 1–5 and the weighted overall score. Open
`agentic_ai/evaluations/eval_results/eval_report_*.txt` for the full report.

---

## 4 · Demo 2 — Full 30-case baseline (slide 20) · ~10 min

```bash
cd agentic_ai/applications

# Single agent
uv run python ../evaluations/run_agent_eval.py --agent single --local --remote

# Handoff multi-agent (auto-switches the backend agent via /agents/set)
uv run python ../evaluations/run_agent_eval.py --agent handoff --local --remote
```

The `--agent` flag now does two things:

1. Calls `POST /agents/set` to swap the backend's active agent module.
2. Tags the run name in Azure AI Foundry as `agent_single | …` / `agent_handoff | …`.

When done:

- Local result JSON: `agentic_ai/evaluations/eval_results/eval_results_<ts>.json`
- Foundry run: https://ai.azure.com → your project → **Evaluations**

> **Pre-staged baselines:** This repo ships with committed reference results at
> `agentic_ai/evaluations/eval_results/baseline_single_30.json` and
> `baseline_handoff_30.json` so attendees can compare their numbers without
> waiting for a full run.

---

## 5 · Demo 3 — Single vs Handoff comparison (slide 15) · 5 sec

```bash
cd agentic_ai/evaluations
uv run python compare_agents.py \
    eval_results/baseline_single_30.json \
    eval_results/baseline_handoff_30.json
```

Prints the side-by-side metric table shown on slide 15.

To compare your **own** runs instead of the pre-staged baselines, point at the
two JSON files your run produced under `eval_results/`.

---

## 6 · Demo 4 — Azure AI Foundry portal (slide 19) · 2 min

1. Go to https://ai.azure.com → select your project.
2. Click **Evaluations** in the left rail.
3. Find runs named `agent_single | Single Turn | <timestamp>` and
   `agent_handoff | Single Turn | <timestamp>`.
4. Select both → **Compare** to see metric-by-metric deltas in the portal UI.

> **Tip:** Pre-stage at least one run before the session by running step 4 once
> beforehand. The Foundry UI takes 1–2 minutes to populate after upload.

---

## 7 · Common issues

| Symptom | Fix |
|---|---|
| `Cannot connect to backend` | Backend not running. Restart Terminal B. |
| `MCP server` warning | Run Terminal A first. Pass `--ci` to skip the prompt. |
| `Missing AZURE_AI_PROJECT_ENDPOINT` | Add it to `.env`. Get URL from ai.azure.com → Project → Settings. |
| Rate-limited during eval | Set `AZURE_OPENAI_EVAL_DEPLOYMENT` to a separate deployment in `.env`. |
| `--agent X` did not switch | Make sure the target module is listed in `AGENT_MODULES` in `.env`. Aliases: `single`, `reflection`, `handoff`, `magentic`. |
| Low scores on all tests | MCP server has no data — confirm Terminal A shows the FastMCP banner and `/health` returns 200. |
| Foundry "Authentication failed" | `az login` and verify **Azure AI Developer** role on the AI project resource. |
| Eval too slow for live demo | Set `REASONING_EFFORT=minimal` (see § 4b below). |

---

## 4b · Speed knob: `REASONING_EFFORT`

When the judge model is a reasoning model (gpt-5+/o-series), default effort is
typically `medium` or `high` and judge calls can dominate run time. The eval
script honours a `REASONING_EFFORT` env var that injects `reasoning_effort`
into every OpenAI chat completion call:

```powershell
$env:REASONING_EFFORT = "minimal"   # or "low" | "medium" | "high"
uv run python ../evaluations/run_agent_eval.py --agent single --local --limit 3 --ci
```

Measured on this repo (5 single-turn cases, gpt-5.2-chat + gpt-5.2 judges):

| Setting | Wall time | Per case | Avg score |
|---|---|---|---|
| `medium` | 7.01 min | 84 s | 3.18 |
| `minimal` | 5.66 min | 68 s | 3.43 |

Use `minimal` for live demos, default/`medium` for committed baselines. See
`docs/MLADS_Agent_Eval/lab_pacing.md` for the full 60-min schedule.

---

## 8 · What's where

```
docs/MLADS_Agent_Eval/
  AI_Agent_Evaluation_Framework_MLADS.pptx   # slide deck
  lab_instructions.md                        # this file
  session_info.txt                           # logistics
  data_sources.md                            # 5-source mapping (slide 1/7/10)

agentic_ai/evaluations/
  README.md                                  # 700-line methodology guide
  eval_dataset.json                          # 30 test cases
  evaluator.py                               # weights + aggregation
  metrics.py                                 # all evaluators
  run_agent_eval.py                          # CLI entry
  compare_agents.py                          # side-by-side comparison
  eval_results/
    baseline_single_30.json                  # slide 20 baseline
    baseline_handoff_30.json                 # slide 15 comparison source
    baseline_README.md                       # how to regenerate

.github/workflows/agent-evaluation.yml       # CI/CD reference (slide 19)
mcp/mcp_service.py                           # 18 MCP tools
```

---

## 9 · After the session

- Open `agentic_ai/evaluations/README.md` for the full methodology, custom-metric
  authoring guide, and CI/CD setup.
- Add your own test cases to `eval_dataset.json` — see "Adding Test Cases" in the
  README.
- Bring your own agent: implement an `Agent` class with the same interface as
  `agents/agent_framework/single_agent.py`, add it to `AGENT_MODULES`, and run
  `--agent <yourname>`.
