# Hosted Agents (Agent Framework + Custom MCP)

This folder demonstrates **Microsoft Foundry Hosted Agents** orchestrated using the **Microsoft Agent Framework**, integrated with a **custom MCP (Model Context Protocol) service)**.  

It provides a minimal setup for exploring hosted agents with your own MCP tools.

---

## Prerequisites

Before starting, ensure you have:

- An Azure subscription
- Azure CLI and Azure Developer CLI (`azd`)
- An MCP service URL ending with `/mcp`  
  (This can be a public MCP or your own MCP hosted in Azure Container Apps)

> ⚠ Hosted Agents are available only in **North Central US**.

---

## Quick Start (Steps 1–5)

### 1. Initialize your project and download a sample agent

```bash
azd init -t https://github.com/Azure-Samples/azd-ai-starter-basic
Enter a unique project name when prompted (e.g., <username>-hosted-agent)

Sign in to Azure:

bash
Copy code
azd auth login
Download a sample agent definition:

bash
Copy code
azd ai agent init -m ../msft-docs-agent/agent.yaml
Notes:

Install the agent extension if prompted

Select your subscription

Select North Central US as the region

Mode SKU: GlobalStandard

Model deployment name: leave default (gpt-4o-mini)

Container memory, CPU, and replicas: leave default (2GB, 1 CPU, min 1 replica, max 3 replicas)

2. Configure your agent for MCP
Copy the environment template:

bash
Copy code
cp .env.example .env
Edit .env and set:

env
Copy code
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=<your-resource-group>
AZURE_LOCATION=northcentralus
MCP_SERVICE_URL=https://<your-mcp-service>/mcp
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
⚠ The MCP_SERVICE_URL must include the /mcp suffix.

3. Deploy the hosted agent
bash
Copy code
azd env new <unique-env-name>
azd up
This provisions:

Microsoft Foundry project

Hosted agent connected to your MCP service

4. Test the agent
Open the Microsoft Foundry portal

Select your project

Start chatting with the hosted agent

5. Clean up resources
To remove all resources created for this hosted agent:

bash
Copy code
azd down
⚠ Deletion may take several minutes. Alternatively, delete the resource group directly in the Azure Portal.

Notes
.env and .azure/ are git-ignored.

Intended for workshop/testing purposes only, not production.

Optional Customization
Modify agent instructions in:

bash
Copy code
contoso-support-agent/main.py
Add or replace MCP tools in:

vbnet
Copy code
custom-mcp/
Attribution
Inspired by the Microsoft Hosted Agent Workshop by Keisuke Hatasaki hosted agent workshop https://github.com/hatasaki/hosted-agent-workshop