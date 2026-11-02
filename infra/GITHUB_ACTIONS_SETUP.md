# GitHub Actions CI/CD Setup Guide

This guide documents how to configure GitHub Actions for automated infrastructure deployment and container builds for the OpenAI Workshop project.

## Overview

The CI/CD pipeline uses:
- **OIDC Authentication** - No secrets stored in GitHub, uses federated identity
- **Remote Terraform State** - Shared state in Azure Storage for team collaboration
- **Per-developer GitHub Environments** - Each developer has their own `integration-<name>` environment backed by their own Azure subscription
- **Environment-scoped Variables** - All Azure credentials and config are stored per-environment, not at repo level

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Actions                               │
├─────────────────────────────────────────────────────────────────────┤
│  orchestrate.yml                                                     │
│    ├── pipeline-config (determine mode + environment)               │
│    │     ├── main branch       → production environment             │
│    │     ├── james-dev branch  → integration-james environment      │
│    │     ├── nicole-dev branch → integration-nicole environment     │
│    │     └── <name>-dev branch → integration-<name> environment     │
│    │                                                                 │
│    ├── [Full Deploy – push / PR → int-agentic / manual]             │
│    │     ├── preflight (enable storage access)                      │
│    │     ├── infrastructure.yml (Terraform deploy)                  │
│    │     ├── docker-application.yml (build backend image)           │
│    │     ├── docker-mcp.yml (build MCP service image)               │
│    │     ├── update-containers.yml (refresh running apps)           │
│    │     ├── integration-tests.yml (smoke tests)                    │
│    │     └── agent-evaluation.yml (AI quality evaluation)           │
│    │                                                                 │
│    └── [Unit Tests Only – PR → main, fork PRs]                       │
│          └── unit-tests (no Azure access)                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ OIDC (no secrets)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Azure (per developer subscription)                  │
├─────────────────────────────────────────────────────────────────────┤
│  ├── App Registration (federated credential for environment)        │
│  ├── Storage Account (Terraform state)                              │
│  ├── Container Registry (Docker images)                             │
│  ├── Container Apps (MCP + Backend)                                 │
│  └── AI Foundry Project (evaluation results, independent lifecycle) │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Azure CLI installed and logged in
- Contributor access to the Azure subscription
- Admin access to the GitHub repository

---

## Step 1: Create Azure App Registration for OIDC

Run the setup script:

```powershell
.\scripts\setup-github-oidc.ps1
```

Or manually:

```powershell
# Variables
$AppName = "GitHub-Actions-OpenAIWorkshop"
$GitHubOrg = "YOUR_GITHUB_ORG"        # e.g., "contoso"
$GitHubRepo = "YOUR_GITHUB_REPO"      # e.g., "OpenAIWorkshop"

# Create App Registration
$app = az ad app create --display-name $AppName --query appId -o tsv

# Create Service Principal
az ad sp create --id $app

# Get IDs
$TenantId = az account show --query tenantId -o tsv
$SubscriptionId = az account show --query id -o tsv
$ObjectId = az ad sp show --id $app --query id -o tsv

Write-Host "Client ID: $app"
Write-Host "Tenant ID: $TenantId"
Write-Host "Subscription ID: $SubscriptionId"
```

## Step 2: Configure Federated Credentials

Create federated credentials for the GitHub environment that maps to this developer.

> **Important:** This repo uses a [customized OIDC subject claim template](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect#customizing-the-subject-claims-for-an-organization-or-repository)
> with `repository_owner_id` and `repository_id` instead of the default `repo:ORG/REPO:...` format.
> All CI jobs bind an `environment:` context, so the OIDC subject includes `environment:<env-name>`.

```powershell
$AppId = "YOUR_APP_ID"  # From Step 1

# ── Per-developer integration environment ──
# Replace <name> with your developer name (e.g., james, nicole, tim)
# The subject must exactly match what GitHub presents in the OIDC token.
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-env-integration-<name>",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repository_owner_id:6154722:repository_id:605201834:environment:integration-<name>",
    "audiences": ["api://AzureADTokenExchange"]
}'

# ── Production environment (only needed for the prod subscription owner) ──
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-env-production",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repository_owner_id:6154722:repository_id:605201834:environment:production",
    "audiences": ["api://AzureADTokenExchange"]
}'

# ── Pull Requests (for PR validation against existing env) ──
# Note: PR jobs also bind environment:, so the subject includes it.
# You may need a credential for the PR context too if your PRs run OIDC.
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-pullrequests",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repository_owner_id:6154722:repository_id:605201834:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
}'
```

> **How to find your IDs:**
> - Owner ID: `gh api repos/microsoft/OpenAIWorkshop --jq '.owner.id'` → `6154722`
> - Repo ID: `gh api repos/microsoft/OpenAIWorkshop --jq '.id'` → `605201834`
> - Check current OIDC template: `gh api repos/microsoft/OpenAIWorkshop/actions/oidc/customization/sub`

## Step 3: Assign Azure Roles

```powershell
$AppId = "YOUR_APP_ID"
$SubscriptionId = "YOUR_SUBSCRIPTION_ID"

# Contributor - for creating resources
az role assignment create `
    --assignee $AppId `
    --role "Contributor" `
    --scope "/subscriptions/$SubscriptionId"

# User Access Administrator - for role assignments
az role assignment create `
    --assignee $AppId `
    --role "User Access Administrator" `
    --scope "/subscriptions/$SubscriptionId"
```

### Step 3b: Assign AI Foundry Evaluation Roles

The agent evaluation pipeline uses an **independent** Azure AI Foundry project (not managed by Terraform).
This avoids `destroy-infrastructure` wiping evaluation history on dev branches.

Assign these roles to the service principal on the pre-existing Foundry resources:

```powershell
$AppId = "YOUR_APP_ID"
$SubscriptionId = "YOUR_SUBSCRIPTION_ID"
$FoundryRG = "ml"                         # Resource group containing the Foundry hub
$HubName = "eastus2"                       # AI Foundry hub workspace name
$AIServicesName = "eastus2oai"              # AI Services account connected to the Foundry project
$StorageName = "steastus2508770413322"      # Foundry's backing storage account

# Azure AI User – read/write access to the Foundry hub and project
az role assignment create `
    --assignee $AppId `
    --role "Azure AI User" `
    --scope "/subscriptions/$SubscriptionId/resourceGroups/$FoundryRG/providers/Microsoft.MachineLearningServices/workspaces/$HubName"

# Cognitive Services OpenAI Contributor – invoke judge models AND push eval results via /openai/evals API
az role assignment create `
    --assignee $AppId `
    --role "Cognitive Services OpenAI Contributor" `
    --scope "/subscriptions/$SubscriptionId/resourceGroups/$FoundryRG/providers/Microsoft.CognitiveServices/accounts/$AIServicesName"

# Storage Blob Data Contributor – upload evaluation data to Foundry storage
az role assignment create `
    --assignee $AppId `
    --role "Storage Blob Data Contributor" `
    --scope "/subscriptions/$SubscriptionId/resourceGroups/$FoundryRG/providers/Microsoft.Storage/storageAccounts/$StorageName"
```

> **Note:** These roles are on the **independent** Foundry resources (RG `ml`), not the
> pipeline-deployed infrastructure. The Foundry project persists across deploy/destroy cycles.

## Step 4: Create Terraform State Storage

```powershell
$RG = "rg-tfstate"
$ACCOUNT = "sttfstateoaiworkshop"  # Must be globally unique
$CONTAINER = "tfstate"
$LOCATION = "eastus2"

# Create resources
az group create --name $RG --location $LOCATION
az storage account create `
    --name $ACCOUNT `
    --resource-group $RG `
    --location $LOCATION `
    --sku Standard_LRS `
    --allow-blob-public-access false

az storage container create `
    --name $CONTAINER `
    --account-name $ACCOUNT `
    --auth-mode login

# Grant access to GitHub Actions service principal
$STORAGE_ID = az storage account show --name $ACCOUNT --resource-group $RG --query id -o tsv
az role assignment create `
    --assignee $AppId `
    --role "Storage Blob Data Contributor" `
    --scope $STORAGE_ID
```

## Step 5: Configure GitHub Environment Variables

All variables are stored at the **environment level** (not repo level). Each developer's
`integration-<name>` environment contains their own Azure subscription credentials.

Go to **GitHub → Repository → Settings → Environments → `integration-<name>` → Environment variables**

### Required Variables (per environment)

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `AZURE_CLIENT_ID` | App Registration Client ID | `1d34c51d-...` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `0fbe7234-...` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `840b5c5c-...` |
| `TFSTATE_RG` | Resource group for TF state | `rg-tfstate` |
| `TFSTATE_ACCOUNT` | Storage account name (globally unique) | `sttfstateoaiworkshop` |
| `TFSTATE_CONTAINER` | Blob container name | `tfstate` |
| `ACR_NAME` | Azure Container Registry name | `OpenAIWorkshopdevacr002` |
| `PROJECT_NAME` | Project identifier | `openaiworkshop` |
| `ITERATION` | Deployment iteration | `002` |
| `AZ_REGION` | Azure region | `eastus2` |
| `DOCKER_IMAGE_MCP` | MCP Docker image name | `mcp-service` |
| `DOCKER_IMAGE_BACKEND` | Backend Docker image name | `backend-service` |
| `REGISTRY_LOGIN_SERVER` | Container registry server | `docker.io` |
| `AZURE_AI_PROJECT_ENDPOINT` | AI Foundry project endpoint for evaluation | `https://...services.ai.azure.com/api/projects/...` |
| `AZURE_OPENAI_EVAL_ENDPOINT` | AI Services endpoint for judge models | `https://...services.ai.azure.com/` |
| `AZURE_OPENAI_EVAL_DEPLOYMENT` | Model deployment for LLM-as-judge | `gpt-5.2` |

### Current Environments

| Environment | Owner | Branch Mapping |
|-------------|-------|----------------|
| `production` | James | `main` |
| `integration-james` | James | `james-dev` |
| `integration-nicole` | Nicole | `nicole-dev` |
| `integration-heena` | Heena | `heena-dev` |
| `integration-tim` | Tim | `tim-dev` |
| `integration-matt` | Matt | `matt-dev` |

---

## Pipeline Modes

The orchestrator has two modes determined by the trigger:

| Trigger | Mode | What runs | Environment |
|---------|------|-----------|-------------|
| **PR → `main`** | Unit tests only | `unit-tests` (no Azure access) | — |
| **PR from a fork** | Unit tests only | `unit-tests` (no Azure access) | — |
| **PR → `int-agentic`** (same repo) | Full deploy (merge commit) | Preflight → Infra → Build → Update → Tests → Eval → Auto-merge | `integration-<name>` |
| **Push to `main`** (after merge) | Full deploy | Preflight → Infra → Build → Update → Tests → Eval | `production` |
| **Push to `<name>-dev`** | Create PR | Creates/updates PR to `int-agentic` | — |
| **Manual dispatch** | Full deploy | Preflight → Infra → Build → Update → Tests → Eval | Chosen env |

### Unit-Tests-Only Mode (PRs to `main`, fork PRs)

PRs to `main` and PRs from forks do **not** access Azure. They run the fast, mock-based
unit/regression tests only. Changes reaching `main` have already been deployed and
integration-tested from `int-agentic`, and `production` is deployed only after merge.

> **Security:** The `production` GitHub Environment must have a deployment branch policy
> that allows only `main`, and OIDC federated credentials should use `environment:<name>`
> subjects only (no `pull_request` or branch subjects).

### Full Deploy Mode (Pushes / Manual)

The full pipeline deploys infrastructure via Terraform, builds and pushes Docker images,
updates the Container Apps, and then runs integration tests against the freshly deployed
environment.

## Workflow Files

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `orchestrate.yml` | PRs, push to main/*-dev, manual | Orchestrates full-deploy or unit-tests-only pipeline |
| `infrastructure.yml` | Called by orchestrate (full deploy) | Terraform plan/apply |
| `docker-application.yml` | Called by orchestrate (full deploy) | Build backend container |
| `docker-mcp.yml` | Called by orchestrate (full deploy) | Build MCP container |
| `update-containers.yml` | Called by orchestrate (full deploy) | Refresh Container Apps |
| `destroy.yml` | Manual dispatch only | Terraform destroy |
| `agent-evaluation.yml` | Called by orchestrate (full deploy) | AI quality evaluation via Azure AI Foundry |
| `integration-tests.yml` | Called by orchestrate (both modes) | Run pytest integration tests |

## Branch to Environment Mapping

| Branch | Environment | Persistent |
|--------|-------------|------------|
| `main` | `production` | ✅ Yes |
| `james-dev` | `integration-james` | ✅ Yes |
| `nicole-dev` | `integration-nicole` | ✅ Yes |
| `heena-dev` | `integration-heena` | ✅ Yes |
| `tim-dev` | `integration-tim` | ✅ Yes |
| `matt-dev` | `integration-matt` | ✅ Yes |
| `<name>-dev` | `integration-<name>` | ✅ Yes |

> All environments persist their infrastructure. To tear down manually, use
> `workflow_dispatch` → `destroy.yml` with the target environment.

---

## Developer Onboarding

To add a new developer to the pipeline:

1. **Create an Azure App Registration** in the developer's own Azure tenant (Step 1 above)
2. **Add a federated credential** with subject `repository_owner_id:6154722:repository_id:605201834:environment:integration-<name>` (Step 2 above)
3. **Assign Azure roles** to the service principal (Steps 3 and 3b above)
4. **Create TF state storage** in the developer's subscription (Step 4 above)
5. **Ask a repo admin** to create the `integration-<name>` GitHub Environment and set the 16 environment variables (Step 5 above)
6. **Developer pushes to `<name>-dev`** branch — the pipeline will pick up the environment automatically

---

## Manual Deployment (Local)

For local development without GitHub Actions:

```powershell
cd infra/terraform

# Deploy with local state (default)
./deploy.ps1 -Environment dev

# Deploy with remote state (team collaboration)
$env:TFSTATE_RG = "rg-tfstate"
$env:TFSTATE_ACCOUNT = "sttfstateoaiworkshop"
$env:TFSTATE_CONTAINER = "tfstate"
$env:TFSTATE_KEY = "local-dev.tfstate"
./deploy.ps1 -Environment dev -RemoteBackend
```

---

## Troubleshooting

### OIDC Login Fails (AADSTS700213)
- **Most common cause:** Subject claim format mismatch. GitHub orgs with a customized OIDC subject
  claim template use `repository_owner_id:<id>:repository_id:<id>:...` instead of `repo:org/repo:...`.
  Check the error message for the `subject` value GitHub is presenting, and update the federated
  credential to match exactly.
- Verify federated credential subject matches exactly what GitHub presents in the OIDC token
- Find your org's subject format: look at the error's `subject` field, or check with
  `gh api orgs/{org}/actions/oidc/customization/sub`
- Check the App Registration has a service principal created
- Ensure role assignments are at subscription scope

### Terraform State Lock
- State is locked during operations
- If stuck, check Azure Storage for lease on the state blob
- Break lease: `az storage blob lease break --blob-name STATE_FILE --container-name tfstate --account-name ACCOUNT`

### Container App Not Updating
- Images are pushed but Container Apps use cached images
- The `update-containers.yml` workflow forces a refresh
- Manual: `az containerapp update --name APP_NAME --resource-group RG --image NEW_IMAGE`

### ACR Authentication Fails
- Ensure service principal has `AcrPush` role on the ACR
- OIDC login must happen before `az acr login`

---

## Security Notes

1. **No Secrets in GitHub** - OIDC eliminates the need for stored credentials
2. **Scoped Permissions** - Federated credentials are branch-specific
3. **Private ACR** - Container registry is not publicly accessible
4. **State Encryption** - Terraform state is encrypted at rest in Azure Storage
5. **Environment Protection** - Add required reviewers for `prod` environment in GitHub

---

## Current Configuration

| Setting | Value |
|---------|-------|
| App Registration | `GitHub-Actions-OpenAIWorkshop` |
| Client ID | `1d34c51d-9d49-48f3-9e48-6a0f099c5f03` |
| Tenant ID | `0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9` |
| Subscription ID | `840b5c5c-3f4a-459a-94fc-6bad2a969f9d` |
| TF State Storage | `sttfstateoaiworkshop` |
| TF State Container | `tfstate` |
| TF State RG | `rg-tfstate` |

---

## Files Reference

```
.github/workflows/
├── orchestrate.yml          # Main orchestration workflow
├── infrastructure.yml       # Terraform deployment
├── docker-application.yml   # Backend container build
├── docker-mcp.yml          # MCP container build
├── update-containers.yml    # Container App refresh
├── agent-evaluation.yml     # AI quality evaluation
├── destroy.yml             # Infrastructure teardown
└── readme.md               # Workflow documentation

infra/
├── GITHUB_ACTIONS_SETUP.md  # This file
├── scripts/
│   └── setup-github-oidc.ps1  # OIDC setup script
└── terraform/
    ├── deploy.ps1           # Local deployment script
    ├── providers.tf         # Terraform providers
    ├── providers.tf.local   # Local backend config
    ├── providers.tf.remote  # Remote backend config
    └── *.tfvars            # Environment variables
```
