"""
Fraud Analysis Workflow - Inner Workflow for Fan-Out → Aggregate Pattern.

This workflow handles the complex multi-agent topology:
1. AlertRouter fans out to 3 specialist agents
2. UsagePatternExecutor, LocationAnalysisExecutor, BillingChargeExecutor run in parallel
3. FraudRiskAggregator collects all results and produces FraudRiskAssessment

This is called as an ACTIVITY from the Durable Task orchestration.
No human-in-the-loop here - that's handled by the outer Durable Task layer.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from agent_framework import (
    Agent,
    Executor,
    handler,
    WorkflowBuilder,
    WorkflowContext,
    MCPStreamableHTTPTool,
)
from agent_framework.openai import OpenAIChatClient

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions for Tool Call Extraction
# ============================================================================


def extract_tool_calls(response) -> list[dict]:
    """Extract tool calls from an AgentResponse."""
    tool_calls = []
    call_id_to_index = {}  # Map call_id to tool_calls index
    
    for msg in response.messages:
        for content in msg.contents:
            if content.type == "function_call":
                # Parse arguments if they're a string
                args = getattr(content, "arguments", {})
                if isinstance(args, str):
                    try:
                        import json
                        args = json.loads(args)
                    except:
                        args = {"raw": args}
                
                call_id = getattr(content, "call_id", None)
                idx = len(tool_calls)
                tool_calls.append({
                    "name": getattr(content, "name", "unknown"),
                    "arguments": args,
                    "result": "",
                    "call_id": call_id,
                })
                if call_id:
                    call_id_to_index[call_id] = idx
                    
            elif content.type == "function_result":
                # Match result to existing call by call_id
                call_id = getattr(content, "call_id", None)
                result = getattr(content, "result", None)
                if call_id and call_id in call_id_to_index:
                    idx = call_id_to_index[call_id]
                    result_str = str(result)[:500] if result else ""
                    tool_calls[idx]["result"] = result_str
                    
            elif content.type == "mcp_server_tool_call":
                call_id = getattr(content, "call_id", None)
                idx = len(tool_calls)
                tool_calls.append({
                    "name": getattr(content, "tool_name", "unknown"),
                    "arguments": getattr(content, "arguments", {}),
                    "result": "",
                    "call_id": call_id,
                })
                if call_id:
                    call_id_to_index[call_id] = idx
                    
            elif content.type == "mcp_server_tool_result":
                call_id = getattr(content, "call_id", None)
                output = getattr(content, "output", None)
                if call_id and call_id in call_id_to_index:
                    idx = call_id_to_index[call_id]
                    result_str = str(output)[:500] if output else ""
                    tool_calls[idx]["result"] = result_str
    
    # Remove call_id from final output (not needed for UI)
    for tc in tool_calls:
        tc.pop("call_id", None)
    
    return tool_calls


# ============================================================================
# Message Types (Pydantic models for type-safe messaging)
# ============================================================================


class ToolCallInfo(BaseModel):
    """Information about a tool call made during analysis."""
    name: str
    arguments: dict = {}
    result: str = ""


class SuspiciousActivityAlert(BaseModel):
    """Initial alert from monitoring system."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str = ""
    timestamp: str = ""
    severity: str = "medium"


class UsageAnalysisResult(BaseModel):
    """Result from UsagePatternExecutor."""
    alert_id: str
    risk_score: float
    findings: str
    data_points: list[str] = []
    tool_calls: list[ToolCallInfo] = []


class LocationAnalysisResult(BaseModel):
    """Result from LocationAnalysisExecutor."""
    alert_id: str
    risk_score: float
    findings: str
    locations: list[str] = []
    tool_calls: list[ToolCallInfo] = []


class BillingAnalysisResult(BaseModel):
    """Result from BillingChargeExecutor."""
    alert_id: str
    risk_score: float
    findings: str
    charges: list[str] = []
    tool_calls: list[ToolCallInfo] = []


class FraudRiskAssessment(BaseModel):
    """Final aggregated assessment from FraudRiskAggregator."""
    alert_id: str
    customer_id: int
    overall_risk_score: float
    risk_level: str  # "low", "medium", "high", "critical"
    recommended_action: str  # "clear", "lock_account", "refund_charges", "both"
    reasoning: str
    usage_findings: str
    location_findings: str
    billing_findings: str
    # Step details for UI
    step_details: dict = {}


# ============================================================================
# Executors
# ============================================================================


class AlertRouterExecutor(Executor):
    """Routes incoming alerts to all specialist executors (fan-out)."""

    def __init__(self):
        super().__init__(id="alert_router")

    @handler
    async def handle_alert(
        self, alert: SuspiciousActivityAlert, ctx: WorkflowContext[SuspiciousActivityAlert]
    ) -> None:
        logger.info(f"[AlertRouter] Routing alert {alert.alert_id} to 3 specialist executors")
        
        # Fan-out: send to all 3 specialist executors
        # The workflow edges will handle delivery
        await ctx.send_message(alert, target_id="usage_pattern_executor")
        await ctx.send_message(alert, target_id="location_analysis_executor")
        await ctx.send_message(alert, target_id="billing_charge_executor")


class UsagePatternExecutor(Executor):
    """Analyzes data usage patterns using MCP tools."""

    def __init__(self, mcp_tool: MCPStreamableHTTPTool, chat_client: OpenAIChatClient):
        super().__init__(id="usage_pattern_executor")
        
        # Filter MCP tools for usage analysis
        allowed_tools = ["get_customer_detail", "get_subscription_detail", "get_data_usage", "search_knowledge_base"]
        filtered_functions = [func for func in mcp_tool.functions if func.name in allowed_tools]
        
        self._agent = Agent(
            client=chat_client,
            instructions=(
                "You are a specialist in analyzing customer data usage patterns. "
                "Look for anomalies like sudden spikes, unusual hours, or patterns inconsistent with history. "
                "Use the available tools to gather data and provide a risk score (0.0-1.0) and findings."
            ),
            name="UsagePatternAnalyst",
            tools=filtered_functions,
        )

    @handler
    async def handle_alert(
        self, alert: SuspiciousActivityAlert, ctx: WorkflowContext[UsageAnalysisResult]
    ) -> None:
        logger.info(f"[UsagePatternExecutor] Analyzing alert {alert.alert_id}")
        
        prompt = f"""
Analyze the usage patterns for customer {alert.customer_id}.
Alert type: {alert.alert_type}
Description: {alert.description}
Severity: {alert.severity}

Use tools to gather usage data, then assess the risk.

Respond in this format:
FINDINGS: [Your detailed findings]
RISK_SCORE: [0.0-1.0]
"""
        
        response = await self._agent.run(prompt)
        response_text = response.text if response.text else ""
        
        # Extract tool calls from response
        tool_calls_raw = extract_tool_calls(response)
        tool_calls = [ToolCallInfo(name=tc["name"], arguments=tc.get("arguments", {}), result=tc.get("result", "")) for tc in tool_calls_raw]
        
        # Parse risk score from LLM response (fallback to severity-based)
        risk_score = 0.5
        if "RISK_SCORE:" in response_text:
            try:
                score_line = [line for line in response_text.split("\n") if "RISK_SCORE:" in line][0]
                risk_score = float(score_line.split("RISK_SCORE:")[1].strip())
            except (IndexError, ValueError):
                # Fallback based on severity
                severity_scores = {"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}
                risk_score = severity_scores.get(alert.severity.lower(), 0.5)
        else:
            severity_scores = {"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}
            risk_score = severity_scores.get(alert.severity.lower(), 0.5)
        
        result = UsageAnalysisResult(
            alert_id=alert.alert_id,
            risk_score=risk_score,
            findings=response_text or "Analysis completed",
            data_points=[],
            tool_calls=tool_calls,
        )
        
        logger.info(f"[UsagePatternExecutor] Completed analysis, risk_score={result.risk_score}, tools={[tc.name for tc in tool_calls]}")
        await ctx.send_message(result)


class LocationAnalysisExecutor(Executor):
    """Analyzes geolocation data for anomalies."""

    def __init__(self, mcp_tool: MCPStreamableHTTPTool, chat_client: OpenAIChatClient):
        super().__init__(id="location_analysis_executor")
        
        # Filter MCP tools for location analysis
        allowed_tools = ["get_customer_detail", "get_security_logs", "search_knowledge_base"]
        filtered_functions = [func for func in mcp_tool.functions if func.name in allowed_tools]
        
        self._agent = Agent(
            client=chat_client,
            instructions=(
                "You are a specialist in analyzing geolocation and security patterns. "
                "Look for impossible travel, VPN usage, or login anomalies. "
                "Use the available tools to gather data and provide a risk score (0.0-1.0) and findings."
            ),
            name="LocationAnalysisAgent",
            tools=filtered_functions,
        )

    @handler
    async def handle_alert(
        self, alert: SuspiciousActivityAlert, ctx: WorkflowContext[LocationAnalysisResult]
    ) -> None:
        logger.info(f"[LocationAnalysisExecutor] Analyzing alert {alert.alert_id}")
        
        prompt = f"""
Analyze the location and security patterns for customer {alert.customer_id}.
Alert type: {alert.alert_type}
Description: {alert.description}
Severity: {alert.severity}

Use tools to gather security logs and location data, then assess the risk.

Respond in this format:
FINDINGS: [Your detailed findings]
RISK_SCORE: [0.0-1.0]
"""
        
        response = await self._agent.run(prompt)
        response_text = response.text if response.text else ""
        
        # Extract tool calls from response
        tool_calls_raw = extract_tool_calls(response)
        tool_calls = [ToolCallInfo(name=tc["name"], arguments=tc.get("arguments", {}), result=tc.get("result", "")) for tc in tool_calls_raw]
        
        # Parse risk score from LLM response (fallback to severity-based)
        risk_score = 0.5
        if "RISK_SCORE:" in response_text:
            try:
                score_line = [line for line in response_text.split("\n") if "RISK_SCORE:" in line][0]
                risk_score = float(score_line.split("RISK_SCORE:")[1].strip())
            except (IndexError, ValueError):
                severity_scores = {"low": 0.3, "medium": 0.5, "high": 0.8, "critical": 0.95}
                risk_score = severity_scores.get(alert.severity.lower(), 0.6)
        else:
            severity_scores = {"low": 0.3, "medium": 0.5, "high": 0.8, "critical": 0.95}
            risk_score = severity_scores.get(alert.severity.lower(), 0.6)
        
        result = LocationAnalysisResult(
            alert_id=alert.alert_id,
            risk_score=risk_score,
            findings=response_text or "Analysis completed",
            locations=[],
            tool_calls=tool_calls,
        )
        
        logger.info(f"[LocationAnalysisExecutor] Completed analysis, risk_score={result.risk_score}, tools={[tc.name for tc in tool_calls]}")
        await ctx.send_message(result)


class BillingChargeExecutor(Executor):
    """Analyzes billing and charge patterns."""

    def __init__(self, mcp_tool: MCPStreamableHTTPTool, chat_client: OpenAIChatClient):
        super().__init__(id="billing_charge_executor")
        
        # Filter MCP tools for billing analysis
        allowed_tools = ["get_customer_detail", "get_billing_summary", "get_subscription_detail", 
                         "get_customer_orders", "search_knowledge_base"]
        filtered_functions = [func for func in mcp_tool.functions if func.name in allowed_tools]
        
        self._agent = Agent(
            client=chat_client,
            instructions=(
                "You are a specialist in analyzing billing and charge patterns. "
                "Look for unusual purchases, subscription changes, or payment anomalies. "
                "Use the available tools to gather data and provide a risk score (0.0-1.0) and findings."
            ),
            name="BillingChargeAnalyst",
            tools=filtered_functions,
        )

    @handler
    async def handle_alert(
        self, alert: SuspiciousActivityAlert, ctx: WorkflowContext[BillingAnalysisResult]
    ) -> None:
        logger.info(f"[BillingChargeExecutor] Analyzing alert {alert.alert_id}")
        
        prompt = f"""
Analyze the billing and charge patterns for customer {alert.customer_id}.
Alert type: {alert.alert_type}
Description: {alert.description}
Severity: {alert.severity}

Use tools to gather billing data and orders, then assess the risk.

Respond in this format:
FINDINGS: [Your detailed findings]
RISK_SCORE: [0.0-1.0]
"""
        
        response = await self._agent.run(prompt)
        response_text = response.text if response.text else ""
        
        # Extract tool calls from response
        tool_calls_raw = extract_tool_calls(response)
        tool_calls = [ToolCallInfo(name=tc["name"], arguments=tc.get("arguments", {}), result=tc.get("result", "")) for tc in tool_calls_raw]
        
        # Parse risk score from LLM response (fallback to severity-based)
        risk_score = 0.4
        if "RISK_SCORE:" in response_text:
            try:
                score_line = [line for line in response_text.split("\n") if "RISK_SCORE:" in line][0]
                risk_score = float(score_line.split("RISK_SCORE:")[1].strip())
            except (IndexError, ValueError):
                severity_scores = {"low": 0.2, "medium": 0.4, "high": 0.6, "critical": 0.85}
                risk_score = severity_scores.get(alert.severity.lower(), 0.4)
        else:
            severity_scores = {"low": 0.2, "medium": 0.4, "high": 0.6, "critical": 0.85}
            risk_score = severity_scores.get(alert.severity.lower(), 0.4)
        
        result = BillingAnalysisResult(
            alert_id=alert.alert_id,
            risk_score=risk_score,
            findings=response_text or "Analysis completed",
            charges=[],
            tool_calls=tool_calls,
        )
        
        logger.info(f"[BillingChargeExecutor] Completed analysis, risk_score={result.risk_score}, tools={[tc.name for tc in tool_calls]}")
        await ctx.send_message(result)


# Type alias for fan-in results
AnalysisResult = UsageAnalysisResult | LocationAnalysisResult | BillingAnalysisResult


class FraudRiskAggregatorExecutor(Executor):
    """Aggregates all analysis results and produces final risk assessment.
    
    Receives a list of results from fan-in edges (all 3 specialists at once).
    """

    def __init__(self, chat_client: OpenAIChatClient):
        super().__init__(id="fraud_risk_aggregator")
        self._chat_client = chat_client

    @handler
    async def handle_results(
        self, results: list[AnalysisResult], ctx: WorkflowContext[None, FraudRiskAssessment]
    ) -> None:
        """Handle aggregated results from fan-in (receives list of all 3 results)."""
        logger.info(f"[Aggregator] Received {len(results)} results for aggregation")
        
        # Separate results by type
        usage: UsageAnalysisResult | None = None
        location: LocationAnalysisResult | None = None
        billing: BillingAnalysisResult | None = None
        
        for result in results:
            if isinstance(result, UsageAnalysisResult):
                usage = result
            elif isinstance(result, LocationAnalysisResult):
                location = result
            elif isinstance(result, BillingAnalysisResult):
                billing = result
        
        if not all([usage, location, billing]):
            raise ValueError(f"Expected 3 different result types, got: {[type(r).__name__ for r in results]}")
        
        alert_id = usage.alert_id
        logger.info(f"[Aggregator] Aggregating results for {alert_id}")
        
        # Use LLM to synthesize findings
        agent = Agent(
            client=self._chat_client,
            instructions=(
                "You are a senior fraud analyst synthesizing findings from specialist agents. "
                "Weigh the evidence, calculate an overall risk score, and recommend an action. "
                "Be thorough but decisive. Return a JSON response with the assessment."
            ),
            name="FraudRiskAggregator",
        )
        
        prompt = f"""
Synthesize these fraud analysis findings for alert {alert_id}:

USAGE ANALYSIS (risk: {usage.risk_score}):
{usage.findings}

LOCATION ANALYSIS (risk: {location.risk_score}):
{location.findings}

BILLING ANALYSIS (risk: {billing.risk_score}):
{billing.findings}

Provide:
1. Overall risk score (0.0-1.0)
2. Risk level (low/medium/high/critical)
3. Recommended action (clear/lock_account/refund_charges/both)
4. Reasoning (1-2 sentences)
"""
        
        response = await agent.run(prompt)
        
        # Calculate weighted score
        overall_score = (usage.risk_score * 0.3 + location.risk_score * 0.4 + billing.risk_score * 0.3)
        
        # Determine risk level
        if overall_score >= 0.8:
            risk_level = "critical"
        elif overall_score >= 0.6:
            risk_level = "high"
        elif overall_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Determine recommended action
        if overall_score >= 0.6:
            recommended_action = "lock_account"
        else:
            recommended_action = "clear"
        
        # Helper to safely extract tool calls (handles both ToolCallInfo and dict)
        def safe_tool_calls(tool_calls_list):
            result = []
            for tc in tool_calls_list:
                if hasattr(tc, 'model_dump'):
                    result.append(tc.model_dump())
                elif isinstance(tc, dict):
                    result.append(tc)
                else:
                    result.append({"name": str(tc), "arguments": {}, "result": ""})
            return result
        
        # Build step details for UI
        step_details = {
            "usage_pattern_executor": {
                "status": "completed",
                "risk_score": usage.risk_score,
                "tool_calls": safe_tool_calls(usage.tool_calls),
                "output": usage.findings[:300] if len(usage.findings) > 300 else usage.findings,
            },
            "location_analysis_executor": {
                "status": "completed",
                "risk_score": location.risk_score,
                "tool_calls": safe_tool_calls(location.tool_calls),
                "output": location.findings[:300] if len(location.findings) > 300 else location.findings,
            },
            "billing_charge_executor": {
                "status": "completed",
                "risk_score": billing.risk_score,
                "tool_calls": safe_tool_calls(billing.tool_calls),
                "output": billing.findings[:300] if len(billing.findings) > 300 else billing.findings,
            },
            "fraud_risk_aggregator": {
                "status": "completed",
                "risk_score": overall_score,
                "tool_calls": [],
                "output": f"Aggregated risk: {overall_score:.2f} ({risk_level}). Recommended: {recommended_action}",
            },
        }
        
        assessment = FraudRiskAssessment(
            alert_id=alert_id,
            customer_id=0,  # Would be extracted from original alert
            overall_risk_score=overall_score,
            risk_level=risk_level,
            recommended_action=recommended_action,
            reasoning=response.text if response.text else "Based on aggregated analysis",
            usage_findings=usage.findings,
            location_findings=location.findings,
            billing_findings=billing.findings,
            step_details=step_details,
        )
        
        logger.info(f"[Aggregator] Assessment complete: risk={overall_score:.2f}, action={recommended_action}")
        await ctx.yield_output(assessment)


# ============================================================================
# Workflow Builder
# ============================================================================


def create_fraud_analysis_workflow(
    mcp_tool: MCPStreamableHTTPTool,
    chat_client: OpenAIChatClient,
) -> Any:
    """
    Create the inner fraud analysis workflow.
    
    This workflow handles the fan-out → aggregate pattern:
    - AlertRouter fans out to 3 specialist agents
    - Specialists run in parallel with MCP tools
    - Aggregator waits for all 3 and produces FraudRiskAssessment
    
    Returns:
        Workflow: The built workflow ready to run
    """
    logger.info("[Workflow] Building fraud analysis workflow...")
    
    # Create executors
    alert_router = AlertRouterExecutor()
    usage_executor = UsagePatternExecutor(mcp_tool, chat_client)
    location_executor = LocationAnalysisExecutor(mcp_tool, chat_client)
    billing_executor = BillingChargeExecutor(mcp_tool, chat_client)
    aggregator = FraudRiskAggregatorExecutor(chat_client)
    
    # Build workflow topology
    builder = WorkflowBuilder(start_executor=alert_router)
    
    # Fan-out: Alert Router → 3 Specialists
    builder.add_edge(alert_router, usage_executor)
    builder.add_edge(alert_router, location_executor)
    builder.add_edge(alert_router, billing_executor)
    
    # Fan-in: 3 Specialists → Aggregator
    builder.add_fan_in_edges(
        [usage_executor, location_executor, billing_executor],
        aggregator
    )
    
    workflow = builder.build()
    logger.info("[Workflow] Fraud analysis workflow built successfully")
    
    return workflow


# ============================================================================
# Standalone Test
# ============================================================================


async def main():
    """Test the workflow standalone (without Durable Task)."""
    import asyncio
    import os
    from dotenv import load_dotenv
    from azure.identity import AzureCliCredential
    
    load_dotenv()
    
    # Initialize MCP tool
    mcp_uri = os.getenv("MCP_SERVER_URI", "http://localhost:8000/mcp")
    mcp_tool = MCPStreamableHTTPTool(name="contoso_mcp", url=mcp_uri, timeout=30)
    
    async with mcp_tool:
        # Initialize chat client
        chat_client = OpenAIChatClient(
            credential=AzureCliCredential(),
            model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o"),
        )
        
        # Create workflow
        workflow = create_fraud_analysis_workflow(mcp_tool, chat_client)
        
        # Test alert
        alert = SuspiciousActivityAlert(
            alert_id="TEST-001",
            customer_id=1,
            alert_type="multi_country_login",
            description="Login attempts from USA and Russia within 2 hours",
            timestamp=datetime.now().isoformat(),
            severity="high",
        )
        
        print(f"\n{'='*60}")
        print(f"Running Fraud Analysis Workflow for Alert: {alert.alert_id}")
        print(f"{'='*60}\n")
        
        # Run workflow
        async for event in workflow.run(alert, stream=True):
            print(f"Event: {type(event).__name__}")
            if event.type == "output" and isinstance(event.data, FraudRiskAssessment):
                assessment = event.data
                print(f"\n{'='*60}")
                print("FRAUD RISK ASSESSMENT")
                print(f"{'='*60}")
                print(f"Alert ID: {assessment.alert_id}")
                print(f"Risk Score: {assessment.overall_risk_score:.2f}")
                print(f"Risk Level: {assessment.risk_level}")
                print(f"Recommended Action: {assessment.recommended_action}")
                print(f"Reasoning: {assessment.reasoning}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
