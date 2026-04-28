"""
Hybrid MCP Server — Strict-Schema + Natural-Language tools in one service.

This MCP server demonstrates a realistic MSP / IT security platform that
exposes BOTH kinds of tools through a single endpoint:

  STRICT-SCHEMA tools (Pydantic-validated, drive automation):
    • triage_alert      — raw alert text → SecurityAlert (12 typed fields)
    • assess_threat     — SecurityAlert  → ThreatAssessment (11 typed fields)
    • create_response   — ThreatAssessment + context → IncidentResponse (15 typed fields)

  NATURAL-LANGUAGE tools (conversational, for human consumption):
    • ask_security_advisor — free-form security questions, best practices, policy
    • explain_for_customer — translate a technical incident into plain English
                             for a non-technical customer/executive

WHY this matters:
  Strict-schema tools MUST return exact enums, scores, and lists because their
  output feeds automated systems (endpoint isolation APIs, SLA timers, ticket
  creation, compliance notifications).  Getting severity wrong = wrong SLA =
  contractual breach.

  Natural-language tools are fine with prose because a HUMAN reads the output.
  "What's our patching policy?" doesn't need a Pydantic model — it needs a
  clear, helpful paragraph.

  A real MSP platform needs BOTH.  This demo shows them coexisting in one
  MCP server, with the client agent choosing the right tool for each task.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  FastMCP (stateful, streamable-http, port 8002)         │
  │                                                         │
  │  ┌─ STRICT SCHEMA ──────────────────────────────────┐   │
  │  │ triage_alert    → SecurityAlert (Pydantic)       │   │
  │  │ assess_threat   → ThreatAssessment (Pydantic)    │   │
  │  │ create_response → IncidentResponse (Pydantic)    │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                         │
  │  ┌─ NATURAL LANGUAGE ───────────────────────────────┐   │
  │  │ ask_security_advisor  → free-form text           │   │
  │  │ explain_for_customer  → plain-English narrative  │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                         │
  │  MCP session_id → AgentSession (history preserved)      │
  └─────────────────────────────────────────────────────────┘

Usage:
    cd agentic_ai/agents/mcp_agent_demo
    uv run python mcp_server_hybrid.py

    # Then in another terminal:
    uv run python mcp_client_hybrid.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, cast

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# ── Load credentials ────────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp", ".env")
load_dotenv(env_path)

from agent_framework import Agent, AgentResponse
from agent_framework._sessions import AgentSession
from agent_framework.openai import OpenAIChatClient
from fastmcp import FastMCP
from fastmcp.server.context import Context


# ═══════════════════════════════════════════════════════════════════════════
#  PYDANTIC CONTRACTS — strict schemas for automation-critical tools
# ═══════════════════════════════════════════════════════════════════════════


class AlertSource(str, Enum):
    EDR = "edr"
    SIEM = "siem"
    NETWORK_IDS = "network_ids"
    EMAIL_GATEWAY = "email_gateway"
    VULNERABILITY_SCANNER = "vulnerability_scanner"
    USER_REPORT = "user_report"


class Severity(str, Enum):
    CRITICAL = "critical"       # SLA: 15 min response, 1 hr containment
    HIGH = "high"               # SLA: 30 min response, 4 hr containment
    MEDIUM = "medium"           # SLA: 2 hr response, 24 hr containment
    LOW = "low"                 # SLA: 8 hr response, 72 hr containment
    INFORMATIONAL = "informational"


class AttackVector(str, Enum):
    RANSOMWARE = "ransomware"
    PHISHING = "phishing"
    LATERAL_MOVEMENT = "lateral_movement"
    CREDENTIAL_THEFT = "credential_theft"
    MALWARE_EXECUTION = "malware_execution"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    COMMAND_AND_CONTROL = "command_and_control"
    SUPPLY_CHAIN = "supply_chain"
    UNKNOWN = "unknown"


class ThreatCategory(str, Enum):
    APT = "apt"
    COMMODITY_MALWARE = "commodity_malware"
    INSIDER_THREAT = "insider_threat"
    OPPORTUNISTIC_ATTACK = "opportunistic_attack"
    TARGETED_ATTACK = "targeted_attack"
    FALSE_POSITIVE = "false_positive"


class RemediationAction(str, Enum):
    ISOLATE_ENDPOINT = "isolate_endpoint"
    DISABLE_ACCOUNT = "disable_account"
    BLOCK_IP = "block_ip"
    BLOCK_HASH = "block_hash"
    FORCE_PASSWORD_RESET = "force_password_reset"
    REVOKE_SESSIONS = "revoke_sessions"
    QUARANTINE_EMAIL = "quarantine_email"
    DEPLOY_PATCH = "deploy_patch"
    RESTORE_FROM_BACKUP = "restore_from_backup"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class ResponsePriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ImpactScope(str, Enum):
    SINGLE_ENDPOINT = "single_endpoint"
    MULTIPLE_ENDPOINTS = "multiple_endpoints"
    SUBNET = "subnet"
    SITE = "site"
    TENANT_WIDE = "tenant_wide"
    CROSS_TENANT = "cross_tenant"


# ── Contract: triage_alert output ───────────────────────────────────────────

class SecurityAlert(BaseModel):
    """Structured alert — every field drives downstream automation."""
    alert_id: str = Field(description="Unique alert ID (e.g. ALT-2026-00847)")
    timestamp: str = Field(description="ISO 8601 timestamp of first detection")
    source: AlertSource = Field(description="System that generated the alert")
    severity: Severity = Field(description="Assessed severity level")
    title: str = Field(description="One-line alert title")
    description: str = Field(description="Concise description of observed activity")
    affected_hostname: str = Field(description="Primary affected endpoint hostname")
    affected_ip: str = Field(description="IP address of affected endpoint")
    affected_user: str = Field(description="Username associated with the activity")
    tenant_id: str = Field(description="MSP customer/tenant identifier")
    indicators_of_compromise: list[str] = Field(
        description="IOCs: file hashes, IPs, domains, registry keys"
    )
    raw_log_snippet: str = Field(description="Relevant raw log excerpt (first 500 chars)")


# ── Contract: assess_threat output ──────────────────────────────────────────

class ThreatAssessment(BaseModel):
    """Enriched threat intelligence with confidence scores."""
    alert_id: str = Field(description="Alert ID for traceability")
    threat_category: ThreatCategory = Field(description="Classified threat category")
    attack_vector: AttackVector = Field(description="MITRE ATT&CK vector")
    threat_score: float = Field(ge=0, le=100, description="Threat score 0-100")
    known_threat_actor: str | None = Field(
        description="Known actor/group name, or null"
    )
    mitre_techniques: list[str] = Field(
        description="MITRE ATT&CK technique IDs (e.g. T1003.001)"
    )
    ioc_matches: list[str] = Field(
        description="IOCs that matched threat intel feeds"
    )
    confidence_pct: float = Field(ge=0, le=100, description="Confidence 0-100%")
    is_known_campaign: bool = Field(description="True if matches known campaign")
    recommended_severity_override: Severity | None = Field(
        description="Override severity if intel warrants it, null to keep"
    )
    intel_summary: str = Field(description="Brief threat intel narrative")


# ── Contract: create_response output ────────────────────────────────────────

class IncidentResponse(BaseModel):
    """Automated response plan — drives real-world remediation APIs."""
    incident_id: str = Field(description="Generated incident ID (e.g. INC-2026-00412)")
    alert_id: str = Field(description="Originating alert ID")
    priority: ResponsePriority = Field(description="Response priority P1-P4")
    final_severity: Severity = Field(description="Final severity after all analysis")
    immediate_actions: list[RemediationAction] = Field(
        description="Ordered remediation actions to execute NOW"
    )
    endpoints_to_isolate: list[str] = Field(description="Hostnames to isolate")
    accounts_to_disable: list[str] = Field(description="Accounts to disable/lock")
    ips_to_block: list[str] = Field(description="IPs for firewall blocklist")
    hashes_to_block: list[str] = Field(description="File hashes to block fleet-wide")
    notification_list: list[str] = Field(
        description="Roles/teams to notify (e.g. soc_lead, tenant_admin, ciso)"
    )
    customer_communication_required: bool = Field(
        description="True if MSP must notify customer per SLA"
    )
    compliance_flags: list[str] = Field(
        description="Regulatory flags (e.g. GDPR_72hr, SOX_incident)"
    )
    sla_response_deadline: str = Field(description="ISO 8601 response deadline")
    sla_containment_deadline: str = Field(description="ISO 8601 containment deadline")
    decision_rationale: str = Field(description="Brief explanation of response decisions")


# ═══════════════════════════════════════════════════════════════════════════
#  SERVER
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in mcp/.env")
        sys.exit(1)

    print(f"🔧 Azure OpenAI endpoint : {endpoint}")
    print(f"🔧 Deployment            : {deployment}")

    llm_client = OpenAIChatClient(
        api_key=api_key,
        azure_endpoint=endpoint,
        model=deployment,
        api_version=api_version,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Internal agents (not exposed directly — called by MCP tools) ────

    triage_agent = Agent(
        client=llm_client,
        name="AlertTriageAgent",
        instructions=(
            "You are a Tier-1 SOC analyst performing initial alert triage for a "
            "managed security services provider (MSP). Extract structured data "
            "from raw SIEM/EDR alerts.\n"
            "- Assign severity: critical=active ransomware/data exfil, "
            "high=credential theft/lateral movement, medium=suspicious behavior, "
            "low=policy violation, informational=benign anomaly\n"
            "- Extract ALL IOCs: SHA-256 hashes, IPs, domains, registry keys\n"
            "- alert_id format: ALT-YYYY-NNNNN\n"
            f"- Current UTC time: {now_iso}"
        ),
    )

    threat_agent = Agent(
        client=llm_client,
        name="ThreatIntelAgent",
        instructions=(
            "You are a threat intelligence analyst. Enrich alerts with MITRE ATT&CK "
            "classification and threat intel.\n"
            "- threat_score: base 50, +20 known campaign, +15 credential theft, "
            "+10 per IOC match, -20 likely false positive\n"
            "- confidence_pct: 90%+ only with multiple IOC matches\n"
            "- Override severity ONLY if intel clearly contradicts triage"
        ),
    )

    response_agent = Agent(
        client=llm_client,
        name="ResponseOrchestrator",
        instructions=(
            "You are the automated incident response engine for an MSP platform.\n"
            "SLA matrix: CRITICAL=P1 (15min/1hr), HIGH=P2 (30min/4hr), "
            "MEDIUM=P3 (2hr/24hr), LOW=P4 (8hr/72hr)\n"
            "- Ransomware/data_exfil → isolate + disable accounts\n"
            "- Credential theft → force password reset + revoke sessions\n"
            "- Lateral movement → isolate ALL affected + at-risk endpoints\n"
            "- If data_at_risk AND regulated → add compliance flags\n"
            "- Customer communication required for P1 and P2\n"
            "- incident_id format: INC-YYYY-NNNNN\n"
            f"- Current UTC time: {now_iso}"
        ),
    )

    # Natural-language advisor agent (no strict output — free-form helpful answers)
    advisor_agent = Agent(
        client=llm_client,
        name="SecurityAdvisor",
        instructions=(
            "You are a senior security advisor for a managed IT platform serving "
            "MSP customers. You answer security questions in clear, practical language.\n\n"
            "Topics you cover:\n"
            "- Security best practices (patching, MFA, zero trust, EDR config)\n"
            "- Compliance guidance (SOC 2, HIPAA, GDPR, SOX, NIST CSF)\n"
            "- Incident response procedures and playbook recommendations\n"
            "- Risk assessment methodology and prioritization\n"
            "- Vendor security evaluation\n"
            "- Security architecture review\n\n"
            "Style: concise, practical, actionable. Cite frameworks where relevant. "
            "You are NOT producing structured data for automation — you are helping "
            "humans understand security concepts and make informed decisions."
        ),
    )

    # Customer-facing explanation agent
    explainer_agent = Agent(
        client=llm_client,
        name="CustomerExplainer",
        instructions=(
            "You translate technical security incidents into clear, non-technical "
            "language for MSP customers, executives, and board members.\n\n"
            "Rules:\n"
            "- NO jargon: replace 'lateral movement' with 'the attacker moved between computers'\n"
            "- NO acronyms without explanation: 'EDR (endpoint protection software)'\n"
            "- Include: what happened, what's at risk, what we're doing about it\n"
            "- Tone: professional, reassuring, transparent — not alarmist\n"
            "- Mention specific actions being taken to protect the customer\n"
            "- Keep it under 200 words unless asked for more detail\n\n"
            "Remember: the reader may be a CFO or office manager, not an IT person."
        ),
    )

    # ── Session stores ──────────────────────────────────────────────────
    agent_sessions: dict[str, AgentSession] = {}
    session_turns: dict[str, int] = {}
    # Store typed results per session for cross-tool reference
    session_data: dict[str, dict] = {}

    # ── FastMCP server ──────────────────────────────────────────────────
    mcp_server = FastMCP("HybridSecurityServer")

    # ════════════════════════════════════════════════════════════════════
    #  STRICT-SCHEMA TOOLS — output is Pydantic-validated JSON
    #  These drive automation: isolation APIs, SLA timers, ticket creation
    # ════════════════════════════════════════════════════════════════════

    @mcp_server.tool
    async def triage_alert(
        raw_alert: Annotated[str, "Raw alert text from SIEM/EDR/IDS to triage"],
        ctx: Context,
    ) -> str:
        """[STRICT SCHEMA] Triage a raw security alert into a structured
        SecurityAlert with 12 typed fields (severity enum, IOC list, etc.).
        Output drives SLA timers and downstream automation — must be exact."""
        session_id = ctx.session_id
        await ctx.info(f"Session {session_id[:8]}… — triaging alert (strict schema)")

        _ensure_session(session_id, agent_sessions, session_turns, session_data)
        session_turns[session_id] += 1

        async with triage_agent:
            response: AgentResponse = await triage_agent.run(
                f"Triage this security alert and extract structured data:\n\n{raw_alert}",
                options={"response_format": SecurityAlert},
            )
        alert = cast(SecurityAlert, response.value)

        # Store for cross-tool reference
        session_data[session_id]["last_alert"] = alert.model_dump(mode="json")
        session_data[session_id]["last_alert_model"] = alert

        result = alert.model_dump(mode="json")
        await ctx.info(
            f"✅ SecurityAlert validated: severity={alert.severity.value}, "
            f"host={alert.affected_hostname}, {len(alert.indicators_of_compromise)} IOCs"
        )
        return json.dumps(result, indent=2)

    @mcp_server.tool
    async def assess_threat(
        alert_json: Annotated[str, "SecurityAlert JSON from triage_alert output"],
        ctx: Context,
    ) -> str:
        """[STRICT SCHEMA] Analyze a triaged SecurityAlert with threat intelligence.
        Returns ThreatAssessment with 11 typed fields (MITRE ATT&CK vectors,
        threat score 0-100, confidence %). Drives playbook selection."""
        session_id = ctx.session_id
        await ctx.info(f"Session {session_id[:8]}… — assessing threat (strict schema)")

        _ensure_session(session_id, agent_sessions, session_turns, session_data)
        session_turns[session_id] += 1

        async with threat_agent:
            response: AgentResponse = await threat_agent.run(
                f"Analyze this security alert with threat intelligence:\n\n{alert_json}",
                options={"response_format": ThreatAssessment},
            )
        threat = cast(ThreatAssessment, response.value)

        session_data[session_id]["last_threat"] = threat.model_dump(mode="json")
        session_data[session_id]["last_threat_model"] = threat

        result = threat.model_dump(mode="json")
        await ctx.info(
            f"✅ ThreatAssessment validated: vector={threat.attack_vector.value}, "
            f"score={threat.threat_score:.0f}/100, confidence={threat.confidence_pct:.0f}%"
        )
        return json.dumps(result, indent=2)

    @mcp_server.tool
    async def create_response(
        threat_json: Annotated[str, "ThreatAssessment JSON from assess_threat output"],
        affected_endpoints: Annotated[str, "Comma-separated hostnames of affected endpoints"],
        compromised_accounts: Annotated[str, "Comma-separated compromised user accounts"],
        data_at_risk: Annotated[bool, "Whether sensitive/regulated data may be exposed"],
        ctx: Context,
    ) -> str:
        """[STRICT SCHEMA] Generate an automated incident response plan.
        Returns IncidentResponse with 15 typed fields including ordered
        remediation actions, SLA deadlines, and compliance flags.
        This output DIRECTLY drives endpoint isolation and account lockout APIs."""
        session_id = ctx.session_id
        await ctx.info(f"Session {session_id[:8]}… — creating response plan (strict schema)")

        _ensure_session(session_id, agent_sessions, session_turns, session_data)
        session_turns[session_id] += 1

        endpoints_list = [e.strip() for e in affected_endpoints.split(",")]
        accounts_list = [a.strip() for a in compromised_accounts.split(",")]

        prompt = (
            "Generate the incident response plan with specific automated actions.\n\n"
            f"Threat assessment:\n{threat_json}\n\n"
            f"Affected endpoints: {json.dumps(endpoints_list)}\n"
            f"Compromised accounts: {json.dumps(accounts_list)}\n"
            f"Data at risk: {data_at_risk}\n"
        )

        # Pull in alert context if available
        alert_data = session_data[session_id].get("last_alert")
        if alert_data:
            prompt += f"\nOriginal alert context: severity={alert_data.get('severity')}, tenant={alert_data.get('tenant_id')}\n"

        async with response_agent:
            response: AgentResponse = await response_agent.run(
                prompt,
                options={"response_format": IncidentResponse},
            )
        incident = cast(IncidentResponse, response.value)

        session_data[session_id]["last_response"] = incident.model_dump(mode="json")
        session_data[session_id]["last_response_model"] = incident

        result = incident.model_dump(mode="json")
        await ctx.info(
            f"✅ IncidentResponse validated: {incident.priority.value}, "
            f"{len(incident.immediate_actions)} actions, "
            f"isolate={incident.endpoints_to_isolate}"
        )
        return json.dumps(result, indent=2)

    # ════════════════════════════════════════════════════════════════════
    #  NATURAL-LANGUAGE TOOLS — output is free-form text for humans
    #  No Pydantic validation — prose answers for questions/explanations
    # ════════════════════════════════════════════════════════════════════

    @mcp_server.tool
    async def ask_security_advisor(
        question: Annotated[str, "Any security question — policy, best practices, compliance, architecture"],
        ctx: Context,
    ) -> str:
        """[NATURAL LANGUAGE] Ask a senior security advisor any question.
        Returns a free-form, practical answer. Good for: security policy,
        compliance guidance, best practices, risk methodology, architecture.
        The advisor remembers conversation context within the session."""
        session_id = ctx.session_id
        await ctx.info(f"Session {session_id[:8]}… — consulting advisor (natural language)")

        _ensure_session(session_id, agent_sessions, session_turns, session_data)
        session_turns[session_id] += 1

        session = agent_sessions[session_id]

        # Add incident context if we have it
        context_note = ""
        if session_data[session_id].get("last_alert"):
            alert = session_data[session_id]["last_alert"]
            context_note = (
                f"\n\n[Context: there is an active incident — alert {alert.get('alert_id')}, "
                f"severity {alert.get('severity')}, affecting {alert.get('affected_hostname')} "
                f"at tenant {alert.get('tenant_id')}. Reference this if the question relates to it.]"
            )

        async with advisor_agent:
            response = await advisor_agent.run(
                question + context_note,
                session=session,
            )

        return response.text

    @mcp_server.tool
    async def explain_for_customer(
        incident_context: Annotated[str, "Technical incident details or JSON to translate"],
        audience: Annotated[str, "Who will read this: 'executive', 'office_manager', 'board', or 'technical_lead'"] = "executive",
        ctx: Context = None,
    ) -> str:
        """[NATURAL LANGUAGE] Translate a technical security incident into
        plain English for a non-technical audience. Outputs a clear, jargon-free
        explanation suitable for customer communication. Specify the audience
        to adjust the tone and detail level."""
        session_id = ctx.session_id if ctx else "default"
        if ctx:
            await ctx.info(f"Session {session_id[:8]}… — drafting customer explanation (natural language)")

        _ensure_session(session_id, agent_sessions, session_turns, session_data)
        session_turns[session_id] += 1

        # Build context from session data
        full_context = f"Audience: {audience}\n\nTechnical details:\n{incident_context}"

        # Enrich with any stored incident data
        stored = session_data[session_id]
        if stored.get("last_response"):
            resp = stored["last_response"]
            full_context += (
                f"\n\nIncident response plan:\n"
                f"- Priority: {resp.get('priority')}\n"
                f"- Severity: {resp.get('final_severity')}\n"
                f"- Actions taken: {json.dumps(resp.get('immediate_actions', []))}\n"
                f"- Customer communication required: {resp.get('customer_communication_required')}\n"
                f"- Compliance flags: {json.dumps(resp.get('compliance_flags', []))}\n"
            )

        async with explainer_agent:
            response = await explainer_agent.run(full_context)

        return response.text

    # ── Utility tools ───────────────────────────────────────────────────

    @mcp_server.tool
    async def get_session_info(ctx: Context) -> dict:
        """Get metadata about the current session — turn count, available data."""
        session_id = ctx.session_id
        stored = session_data.get(session_id, {})
        return {
            "session_id": session_id,
            "turn_count": session_turns.get(session_id, 0),
            "has_alert": "last_alert" in stored,
            "has_threat_assessment": "last_threat" in stored,
            "has_response_plan": "last_response" in stored,
            "alert_severity": stored.get("last_alert", {}).get("severity"),
            "incident_priority": stored.get("last_response", {}).get("priority"),
        }

    @mcp_server.tool
    async def reset_session(ctx: Context) -> str:
        """Clear all data and conversation history for the current session."""
        session_id = ctx.session_id
        agent_sessions.pop(session_id, None)
        session_turns.pop(session_id, None)
        session_data.pop(session_id, None)
        return f"Session {session_id[:8]}… cleared — all data and history reset."

    # ── Launch ──────────────────────────────────────────────────────────

    print("──────────────────────────────────────────────────────────────")
    print("🛡️   Hybrid MCP Security Server")
    print("   URL:  http://localhost:8002/mcp")
    print()
    print("   STRICT-SCHEMA tools (automation-critical):")
    print("     • triage_alert      → SecurityAlert (12 fields)")
    print("     • assess_threat     → ThreatAssessment (11 fields)")
    print("     • create_response   → IncidentResponse (15 fields)")
    print()
    print("   NATURAL-LANGUAGE tools (human-facing):")
    print("     • ask_security_advisor   → free-form advisory")
    print("     • explain_for_customer   → plain-English translation")
    print()
    print("   Utility: get_session_info, reset_session")
    print("──────────────────────────────────────────────────────────────")

    mcp_server.run(transport="streamable-http", host="0.0.0.0", port=8002)


def _ensure_session(
    session_id: str,
    sessions: dict[str, AgentSession],
    turns: dict[str, int],
    data: dict[str, dict],
) -> None:
    """Lazily initialize session stores."""
    if session_id not in sessions:
        sessions[session_id] = AgentSession()
        turns[session_id] = 0
        data[session_id] = {}


if __name__ == "__main__":
    main()
