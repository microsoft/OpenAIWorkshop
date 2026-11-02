# CI/CD Pipeline

## Flow

```
*-dev  ──push──▶  CI/CD Pipeline (8 stages)  ──pass──▶  auto-merge PR → int-agentic
                                                                │
int-agentic  ◀──────────────────────────────────────────────────┘
     │
     └──push──▶  promote-to-main.yml  ──▶  creates/updates PR → main
                                                                │
main  ◀──────────  human review + merge  ◀──────────────────────┘
     │
     └──push──▶  CI/CD Pipeline (production deploy)
```

**Doc-only changes** (`.md`, `docs/`, `LICENSE`) are ignored — no pipeline runs.

## Workflows

| File | Trigger | Purpose |
|------|---------|---------|
| `orchestrate.yml` | push to `*-dev`/`main`, PR to `int-agentic`/`main`, manual | Main CI/CD: infra → build → deploy → test → eval → auto-merge |
| `promote-to-main.yml` | push to `int-agentic` | Creates/updates a rolling PR from `int-agentic` → `main` |
| `infrastructure.yml` | called by orchestrate | Terraform plan + apply with auto-import recovery |
| `docker-application.yml` | called by orchestrate | Build & push backend container to ACR |
| `docker-mcp.yml` | called by orchestrate | Build & push MCP container to ACR |
| `update-containers.yml` | called by orchestrate | Deploy new images to Container Apps |
| `integration-tests.yml` | called by orchestrate | API tests against live environment |
| `agent-evaluation.yml` | called by orchestrate | Agent quality eval → Azure AI Foundry |
| `destroy.yml` | manual dispatch | Terraform destroy for a target environment |

## Pipeline Stages

| # | Stage | Push | PR |
|---|-------|------|----|
| 0 | **pipeline-config** — resolve environment & mode | ✅ | ✅ |
| — | **unit-tests** — fast regression tests (no Azure) | ✅ | ✅ |
| 1 | **preflight** — unlock TF state storage | ✅ | ✅* |
| 2 | **deploy-infrastructure** — Terraform | ✅ | ✅* |
| 3 | **build containers** (backend + MCP, parallel) | ✅ | ✅* |
| 4 | **update-containers** — deploy to Container Apps | ✅ | ✅* |
| 5 | **integration-tests** | ✅ | ✅* |
| 6 | **agent-evaluation** → Foundry | ✅ | ✅* |
| 7 | **auto-merge** — squash-merge dev PR → int-agentic | — | ✅* |

\* PRs to `int-agentic` from branches in this repository only (deploys the merge commit to the developer's `integration-<name>` environment).  
PRs to `main` and PRs from forks run **unit tests only** and never access Azure.

## Security Model

- The `production` environment has a deployment branch policy that only allows `main`. Pull requests never use `production`.
- PRs from forks never resolve an Azure environment.
- Branch names and dispatch inputs are passed to scripts via `env:` (never interpolated into `run:`), and the resolved environment name is validated.
- OIDC federated credentials should be scoped to `environment:<name>` subjects only (no `pull_request` or branch subjects).

## Per-Developer Environments

Each developer has their own GitHub Environment (`integration-<name>`) with their own Azure subscription and OIDC credentials. All config is stored as **environment-level variables** (zero repo-level variables).

Branch mapping: `james-dev` → `integration-james`, `main` → `production`

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | App registration client ID (OIDC) |
| `AZURE_TENANT_ID` | Entra ID tenant |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `AZ_REGION` | Azure region |
| `PROJECT_NAME` | Project name (e.g. `OpenAIWorkshop`) |
| `ITERATION` | Deployment iteration (e.g. `002`) |
| `TFSTATE_ACCOUNT` | TF state storage account |
| `TFSTATE_CONTAINER` | TF state blob container |
| `TFSTATE_RG` | TF state resource group |
| `MCP_SERVER_URI` | MCP service URI |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat model deployment |
| `AZURE_OPENAI_EVAL_DEPLOYMENT` | Eval model deployment |
| `AZURE_AI_PROJECT_ENDPOINT` | AI Foundry project endpoint |

## Azure Setup

1. Azure subscription with a resource group + storage account for Terraform state
2. App registration with OIDC federated credentials for each GitHub Environment:
   ```
   Subject: repo:microsoft/OpenAIWorkshop:environment:<env-name>
   ```