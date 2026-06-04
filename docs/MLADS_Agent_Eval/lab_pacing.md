# Lab Pacing Guide — 60-Minute Session

This guide helps you sequence the MLADS Agent Eval lab to fit in **60 minutes**
while still showing a real eval running live, comparing two agent variants, and
viewing results in Azure AI Foundry.

---

## Measured timings (gpt-5.2-chat agent + gpt-5.2 judges, eastus2)

| Configuration | Cases | Wall time | Per case | Notes |
|---|---|---|---|---|
| **Single agent** baseline (default effort) | 30 (25s + 5mt) | **~30 min** | ~60 s | `baseline_single_30.json` |
| **Handoff agent** baseline (default effort) | 30 (25s + 5mt) | **~30 min** | ~60 s | `baseline_handoff_30.json` |
| **Reflection agent** baseline (default effort) | 30 (25s + 5mt) | **50 min** | ~100 s | `baseline_reflection_30.json` — self-critique loop doubles per-case cost |
| `--limit 5 --single-turn-only REASONING_EFFORT=medium` | 5 | **7.0 min** | 84 s | Default-ish judge depth |
| `--limit 5 --single-turn-only REASONING_EFFORT=minimal` | 5 | **5.7 min** | 68 s | **~19 % faster, equal quality** |
| `--limit 3 --single-turn-only REASONING_EFFORT=minimal` | 3 (estimated) | **~3.4 min** | 68 s | Best fit for live demo slot |

> Use `REASONING_EFFORT=minimal` (or `low`) for live demos.
> Use default / medium for committed baselines so they're more representative.

### Key insight from full-baseline timings

The **reflection agent takes ~67 % longer** than single/handoff (50 min vs 30 min) because each user query triggers a self-critique loop (initial response → critique → refined response). The judges then have a longer transcript to evaluate. The quality lift is modest on this dataset (+3.4 pp pass rate, +0.04 avg score, +0.17 Fluency, –0.20 Intent Resolution) — a real-world trade-off worth highlighting.

---

## Recommended 60-min agenda

| Min | Activity | Slides | What's happening |
|----:|---|---|---|
| 0–5 | Welcome, why evals matter | 1–3 | No live work |
| 5–13 | Concept tour: eval types, graders, single vs multi-turn | 4, 5, 6, 11 | No live work |
| 13–18 | Eval-driven dev + scoring philosophy | 13, 16, 17 | No live work |
| 18–23 | Workshop scenario intro: 18 tools, 30 scenarios, 5 sources | 7, 8, 9, 10 | `data_sources.md` opened in case of questions |
| 23–28 | Eval design: built-in + custom, multi-grader arch | 12, 14, 18 | No live work |
| **28–35** | **🎬 Live demo: run `--limit 3` against single agent** | 18, 19 | See "Live demo" below — ~4 min eval + 3 min walkthrough |
| 35–40 | Walk through pre-staged 30-case results | 20 (with v2 numbers) | `eval_results/baseline_single_30.json` |
| 40–45 | Single vs Handoff comparison | 15 (with v2 numbers) | `compare_agents.py` against pre-staged baselines (5 sec) |
| 45–48 | Azure AI Foundry portal walk-through | 19 | Pre-staged Foundry run from `--remote` push (instant) |
| 48–55 | Customer conversation playbook | 21, 22, 23 | No live work |
| 55–60 | Q&A | 24 | — |

---

## Live demo (~7 min of the slot)

**Prep before the session (do once at lectern, before attendees arrive):**

```powershell
# Terminal A — MCP
cd mcp; uv run python mcp_service.py

# Terminal B — backend
cd agentic_ai/applications
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
uv run uvicorn backend:app --port 7000
```

**Run during the demo slot (Terminal C):**

```powershell
cd agentic_ai/applications
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
$env:REASONING_EFFORT="minimal"     # ← fast judges for live demo

uv run python ../evaluations/run_agent_eval.py `
    --agent single --local --limit 3 --single-turn-only --ci
```

**What attendees see (≈ 4 min):**

1. Backend agent is auto-switched to single agent (`POST /agents/set`)
2. Three test cases stream through: query → tool calls → response
3. Multi-grader scoring runs: deterministic graders + LLM judges
4. Final summary table prints with per-metric breakdown

**Then (~ 3 min) walk through:**

- `eval_results/eval_report_*.txt` — per-case detail
- `compare_agents.py eval_results/baseline_single_30.json eval_results/baseline_handoff_30.json`
- The Foundry portal tab (pre-loaded)

---

## Reducing risk

| Risk | Mitigation |
|---|---|
| Live eval slower than expected | Have screenshots of a recent successful run ready as a fallback |
| Backend or MCP crashed at break time | Run `curl http://localhost:7000/auth/config` and `curl http://localhost:8000/health` to confirm before starting demo |
| Azure OpenAI rate-limited | Use `--limit 3` not `--limit 5`. Have `REASONING_EFFORT=minimal` set. Have a separate `AZURE_OPENAI_EVAL_DEPLOYMENT` to spread quota |
| Foundry remote eval still uploading at demo time | Skip `--remote` for the live demo (already pre-staged baselines have it) |
| Conference Wi-Fi flaky | Demo can run fully offline against local MCP + local backend if `--local` only (no `--remote`) |

---

## Setting reasoning effort

The repo's `run_agent_eval.py` now honours a `REASONING_EFFORT` env var:

```powershell
$env:REASONING_EFFORT = "minimal"   # or "low" | "medium" | "high"
```

It monkey-patches the OpenAI chat-completions call to inject `reasoning_effort`
on every request — both for the Azure AI Evaluation SDK judges and for the
custom solution-accuracy grader. Without setting the env var, the agent and
judges use whatever the model deployment's default is (usually `medium` or
`high` for reasoning models).

For **published baselines** (committed to repo), use default / medium so the
numbers are conservative and reproducible. For **live demos**, use `minimal`
to keep latency low.
