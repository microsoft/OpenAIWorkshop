# 🧪 Lab Setup Card — Print or Pin Up

> One-page reference for attendees of *From Prototype to Production: Rigorous
> AI Agent Evaluation*. Fits on a single side of A4 / Letter.

---

## ① Prerequisites  (5 min, do once)

```bash
git clone https://github.com/microsoft/OpenAIWorkshop
cd OpenAIWorkshop
uv sync                                # root + workspace deps
az login                               # for DefaultAzureCredential
```

**`.env` file** (`agentic_ai/applications/.env`) — copy from `.env.sample` and set:

```bash
AZURE_OPENAI_ENDPOINT="https://<your-aoai>.openai.azure.com"
AZURE_OPENAI_API_KEY="<key>"           # or comment out → uses az login
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-5.2-chat"
AZURE_OPENAI_EVAL_DEPLOYMENT="gpt-5.2"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small"
AZURE_OPENAI_API_VERSION="2025-03-01-preview"
AZURE_AI_PROJECT_ENDPOINT="https://<acc>.services.ai.azure.com/api/projects/<proj>"
MCP_SERVER_URI="http://localhost:8000/mcp"
DISABLE_AUTH="true"
AGENT_MODULES="agents.agent_framework.single_agent,agents.agent_framework.multi_agent.reflection_agent,agents.agent_framework.multi_agent.handoff_multi_domain_agent,agents.agent_framework.multi_agent.magentic_group"
```

---

## ② Start Services  (two terminals, leave running)

### Terminal A — MCP server (port 8000)

```bash
cd mcp
uv run python mcp_service.py
# wait for "Uvicorn running on http://0.0.0.0:8000"
```

### Terminal B — Agent backend (port 7000)

```powershell
cd agentic_ai/applications
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
uv run uvicorn backend:app --port 7000
# wait for "Application startup complete"
```

---

## ③ Verify, then Run

### Sanity check (Terminal C)

```bash
curl http://localhost:8000/health        # MCP
curl http://localhost:7000/auth/config   # backend
```

### Live demo (fast judges, ~4 min)

```powershell
cd agentic_ai/applications
$env:REASONING_EFFORT="minimal"
uv run python ../evaluations/run_agent_eval.py `
    --agent single --local --limit 3 --single-turn-only --ci
```

You should see `✓ Backend agent switched to: agents.agent_framework.single_agent`
followed by `[1/3]`, `[2/3]`, `[3/3]` progress, then a metric breakdown table.

### Compare two committed baselines (instant)

```powershell
cd agentic_ai/evaluations
uv run python compare_agents.py `
    eval_results/baseline_single_30.json `
    eval_results/baseline_handoff_30.json
```

---

## 🆘 Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot connect to backend` | Restart Terminal B |
| `MCP server` warning | Start Terminal A first; or pass `--ci` to skip prompt |
| `Missing AZURE_AI_PROJECT_ENDPOINT` | Add it to `.env` (only needed for `--remote`) |
| `--agent X` did not switch | Make sure module is in `AGENT_MODULES` in `.env` |
| 401 Auth error | Re-run `az login`; or set a valid `AZURE_OPENAI_API_KEY` |
| Eval too slow | Set `$env:REASONING_EFFORT="minimal"` |

---

## 📚 More

| | |
|---|---|
| Full walk-through | `docs/MLADS_Agent_Eval/lab_instructions.md` |
| 60-min agenda + timings | `docs/MLADS_Agent_Eval/lab_pacing.md` |
| Eval methodology (700 lines) | `agentic_ai/evaluations/README.md` |
| Data-source mapping | `docs/MLADS_Agent_Eval/data_sources.md` |
| Regenerate deck | `python docs/MLADS_Agent_Eval/update_slides.py` |
