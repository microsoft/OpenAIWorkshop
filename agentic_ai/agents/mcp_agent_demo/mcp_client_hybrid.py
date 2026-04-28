"""
Hybrid MCP Client — demonstrates calling BOTH strict-schema and
natural-language tools from the same MCP server in one incident flow.

This client simulates a realistic MSP SOC workflow:

  Phase 1 (STRICT SCHEMA):
    1. Feed a raw EDR alert → triage_alert → SecurityAlert (Pydantic)
    2. Pass SecurityAlert  → assess_threat → ThreatAssessment (Pydantic)
    3. Pass ThreatAssessment → create_response → IncidentResponse (Pydantic)

  Phase 2 (NATURAL LANGUAGE):
    4. "What's our SLA obligation for this severity?" → ask_security_advisor
    5. "Draft a customer notification"  → explain_for_customer

  The point: strict schema for automation (isolation, blocking, SLA timers),
  natural language for humans (advisor questions, customer emails).
  Same server, same session, both tool types working together.

Prerequisites:
    mcp_server_hybrid.py must be running on http://localhost:8002/mcp

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python mcp_client_hybrid.py
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", ".env")
load_dotenv(env_path)

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient

# ── The same raw EDR alert used in the typed-contracts demo ─────────────────

RAW_ALERT = """
=== EDR ALERT — Managed Endpoint Security ===
Timestamp: 2026-02-19T14:23:17Z
Source: Endpoint Detection & Response (EDR Agent v4.2)
Tenant: Contoso Financial Services (tenant: contoso-fin-2024)

ALERT: Suspicious PowerShell execution detected on CONTOSO-DC01

Endpoint: CONTOSO-DC01 (10.42.1.5) — Domain Controller
User Context: CONTOSO\\svc_backup (service account)

Observed Activity:
- PowerShell process spawned by svc_backup at 14:23:17Z
- Encoded command detected: Base64-encoded Invoke-Mimikatz variant
- LSASS memory access attempted (credential dumping pattern)
- Outbound connection to 185.220.101.42:443 (known C2 infrastructure)
- Kerberos ticket request anomaly: TGT requested for domain admin group
- Shadow copy deletion command queued (vssadmin delete shadows)

File Hash (SHA-256): a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890
Secondary Hash: f0e1d2c3b4a596870fedcba9876543210fedcba9876543210fedcba987654321
DNS Query: update-service.kfrp[.]xyz (suspicious DGA-like domain)

Additional Telemetry:
- 3 failed RDP attempts from CONTOSO-WS-047 to CONTOSO-DC01 prior to event
- svc_backup account password last changed 847 days ago
- Similar PowerShell pattern seen on CONTOSO-FS01 (file server) 47 min earlier
- No MFA enforcement on service accounts per tenant policy

Raw Log: EventID=4688|ProcessName=powershell.exe|CommandLine=-enc
SQBtAHAAbwByAHQALQBNAG8AZAB1AGwAZQAgAC4AXABJAHaA...|ParentProcess=cmd.exe
|User=CONTOSO\\svc_backup|LogonType=3|SourceIP=10.42.3.47
"""


async def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in mcp/.env")
        sys.exit(1)

    mcp_url = "http://localhost:8002/mcp"
    print("=" * 78)
    print("🛡️   HYBRID MCP DEMO — Strict Schema + Natural Language in One Server")
    print("=" * 78)
    print()
    print("  This demo processes a security incident through the SAME MCP server")
    print("  using BOTH tool types:")
    print()
    print("  Phase 1 — STRICT SCHEMA (drives automation):")
    print("    triage_alert → assess_threat → create_response")
    print("    Output: Pydantic-validated JSON → APIs, SLA timers, tickets")
    print()
    print("  Phase 2 — NATURAL LANGUAGE (helps humans):")
    print("    ask_security_advisor → explain_for_customer")
    print("    Output: plain English prose → analysts, customers, executives")
    print()
    print(f"  Connecting to: {mcp_url}")
    print()

    async with MCPStreamableHTTPTool(
        name="security_ops",
        description=(
            "Hybrid security operations server with BOTH strict-schema tools "
            "(triage_alert, assess_threat, create_response) AND natural-language "
            "tools (ask_security_advisor, explain_for_customer). Use strict tools "
            "for structured incident data, natural tools for human questions."
        ),
        url=mcp_url,
    ) as mcp_tool:
        tool_names = [t.name for t in mcp_tool.functions]
        print(f"  ✅ Connected — {len(tool_names)} tools: {', '.join(tool_names)}")
        print()

        client = OpenAIChatClient(
            api_key=api_key,
            azure_endpoint=endpoint,
            model=deployment,
            api_version=api_version,
        )

        async with Agent(
            client=client,
            name="SOC_Analyst",
            instructions=(
                "You are a SOC analyst using a hybrid security operations platform.\n\n"
                "You have access to TWO TYPES of tools:\n\n"
                "STRICT-SCHEMA tools (for automation — always use these for incident data):\n"
                "  • triage_alert: Pass raw alert text → get SecurityAlert JSON\n"
                "  • assess_threat: Pass SecurityAlert JSON → get ThreatAssessment JSON\n"
                "  • create_response: Pass ThreatAssessment JSON + endpoint/account details\n"
                "    → get IncidentResponse JSON\n\n"
                "NATURAL-LANGUAGE tools (for human questions and communication):\n"
                "  • ask_security_advisor: Ask any security policy/practice question\n"
                "  • explain_for_customer: Translate technical details to plain English\n\n"
                "RULES:\n"
                "1. For incident processing, ALWAYS use strict-schema tools in order\n"
                "2. Pass the FULL JSON output from one strict tool as input to the next\n"
                "3. For questions about policy/practice/SLA, use ask_security_advisor\n"
                "4. For customer communication, use explain_for_customer\n"
                "5. Present strict-schema results with key fields highlighted\n"
                "6. Present natural-language results as-is with brief intro\n"
                "7. Do NOT reformulate or summarize the raw alert — pass it directly"
            ),
            tools=mcp_tool,
        ) as analyst:

            # ════════════════════════════════════════════════════════════
            #  PHASE 1 — STRICT SCHEMA: Incident processing pipeline
            # ════════════════════════════════════════════════════════════

            print("━" * 78)
            print("  PHASE 1 │ STRICT-SCHEMA TOOLS — Incident Processing Pipeline")
            print("━" * 78)

            # Step 1: Triage
            print()
            print("  STEP 1 │ triage_alert: Raw EDR → SecurityAlert (12 typed fields)")
            print("  " + "─" * 60)
            r1 = await analyst.run(
                f"Triage this raw alert using the triage_alert tool. "
                f"Pass the ENTIRE raw text:\n\n{RAW_ALERT}"
            )
            print(f"\n  🤖 Analyst:\n{_indent(r1.text)}")

            # Step 2: Threat Assessment (pass Step 1 output explicitly)
            print()
            print("  STEP 2 │ assess_threat: SecurityAlert → ThreatAssessment (11 typed fields)")
            print("  " + "─" * 60)
            r2 = await analyst.run(
                "Now pass this SecurityAlert JSON to assess_threat for "
                "threat intelligence analysis. Here is the SecurityAlert "
                f"output from the previous step:\n\n{r1.text}"
            )
            print(f"\n  🤖 Analyst:\n{_indent(r2.text)}")

            # Step 3: Response Plan (pass Step 2 output explicitly)
            print()
            print("  STEP 3 │ create_response: ThreatAssessment → IncidentResponse (15 typed fields)")
            print("  " + "─" * 60)
            r3 = await analyst.run(
                "Now create an incident response plan using create_response. "
                "Pass this ThreatAssessment JSON along with "
                "affected_endpoints='CONTOSO-DC01,CONTOSO-FS01', "
                "compromised_accounts='CONTOSO\\\\svc_backup,domain_admin', and "
                f"data_at_risk=true.\n\nThreatAssessment from previous step:\n\n{r2.text}"
            )
            print(f"\n  🤖 Analyst:\n{_indent(r3.text)}")

            # ════════════════════════════════════════════════════════════
            #  PHASE 2 — NATURAL LANGUAGE: Human-facing tools
            # ════════════════════════════════════════════════════════════

            print()
            print("━" * 78)
            print("  PHASE 2 │ NATURAL-LANGUAGE TOOLS — Human-Facing Communication")
            print("━" * 78)

            # Step 4: Ask advisor
            print()
            print("  STEP 4 │ ask_security_advisor: Policy/SLA question (free-form answer)")
            print("  " + "─" * 60)
            r4 = await analyst.run(
                "Ask the security advisor: Given this incident involves credential "
                "theft on a domain controller for a financial services tenant, "
                "what are our SOC 2 and SOX compliance notification obligations? "
                "What's the timeline?\n\n"
                f"Incident context from prior steps:\n{r3.text}"
            )
            print(f"\n  🤖 Analyst:\n{_indent(r4.text)}")

            # Step 5: Customer explanation
            print()
            print("  STEP 5 │ explain_for_customer: Plain-English customer notification")
            print("  " + "─" * 60)
            r5 = await analyst.run(
                "Now use explain_for_customer to draft a notification for the "
                "Contoso Financial Services executive team (audience: 'executive'). "
                "Summarize the incident and what we're doing about it — no jargon.\n\n"
                f"Full incident context:\n{r3.text}"
            )
            print(f"\n  🤖 Analyst:\n{_indent(r5.text)}")

            # ════════════════════════════════════════════════════════════
            #  SUMMARY
            # ════════════════════════════════════════════════════════════

            print()
            print("=" * 78)
            print("📊  DEMO SUMMARY — Same server, two tool types, one incident")
            print("=" * 78)
            print("""
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STRICT-SCHEMA TOOLS            │  NATURAL-LANGUAGE TOOLS             │
  │  (Pydantic-validated JSON)      │  (Free-form prose)                  │
  ├────────────────────────────────────────────────────────────────────────┤
  │                                 │                                     │
  │  triage_alert                   │  ask_security_advisor               │
  │    → SecurityAlert (12 fields)  │    → "Our SOC 2 obligations        │
  │    → severity=HIGH (not "bad")  │       require notification within   │
  │    → Starts 30-min SLA timer    │       24 hours..."                  │
  │                                 │    → Human reads, understands,      │
  │  assess_threat                  │       makes decision                │
  │    → ThreatAssessment (11 flds) │                                     │
  │    → attack_vector=CRED_THEFT   │  explain_for_customer               │
  │    → Selects Mimikatz playbook  │    → "We detected unauthorized     │
  │                                 │       access to your network..."    │
  │  create_response                │    → CFO reads this, not the JSON   │
  │    → IncidentResponse (15 flds) │                                     │
  │    → isolate_endpoint API call  │                                     │
  │    → disable_account API call   │                                     │
  │    → block_ip firewall rule     │                                     │
  │                                 │                                     │
  │  WHO READS THIS: machines       │  WHO READS THIS: humans             │
  │  → APIs, automation, tickets    │  → analysts, customers, executives  │
  └────────────────────────────────────────────────────────────────────────┘

  Both tool types coexist in ONE MCP server, ONE session, ONE incident.
  The right tool for the right job.
""")
            print("=" * 78)
            print("✅  Hybrid demo complete — strict schemas for machines, prose for people.")
            print("=" * 78)

    print()


def _indent(text: str, prefix: str = "    ") -> str:
    """Indent each line of text for nicer console output."""
    return "\n".join(f"{prefix}{line}" for line in text.split("\n"))


if __name__ == "__main__":
    asyncio.run(main())
