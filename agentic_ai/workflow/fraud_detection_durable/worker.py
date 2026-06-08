"""
Durable Task Worker for Fraud Detection.

Hybrid architecture combining:
- DurableAIAgentWorker: Registers FraudAnalysisAgent as a durable entity with
  persistent conversation state (DurableAgentState)
- DurableAIAgentOrchestrationContext: Type-safe agent calls from within orchestrations
- Inner Workflow: Complex fan-out/fan-in topology with MCP tools for fast execution
- DTS Orchestration: Durability, HITL, timeouts, crash recovery, feedback loop

The FraudAnalysisAgent entity preserves conversation history across invocations,
enabling stateful re-investigation when an analyst rejects and provides feedback.

Prerequisites:
- Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_CHAT_DEPLOYMENT
- Start Durable Task Scheduler emulator
- Start MCP Server: cd mcp && uv run mcp_service.py
"""

import asyncio
import json
import logging
import os
import sys
from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Force UTF-8 console so emoji/unicode in logs never crash on Windows cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load environment first so observability can read connection string
load_dotenv()

# ------------------------------------------------------------------
# Observability (must be before any agent imports)
# ------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # agentic_ai/

try:
    from observability import setup_observability
    _observability_enabled = setup_observability(
        service_name="contoso-fraud-worker",
        enable_live_metrics=True,
        enable_sensitive_data=os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() in ("1", "true", "yes"),
    )
except ImportError:
    _observability_enabled = False

# ------------------------------------------------------------------
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker
from durabletask.task import ActivityContext, OrchestrationContext, Task, when_any
from pydantic import BaseModel, ValidationError

from agent_framework import (
    AgentResponse,
    BaseAgent,
    Content,
    MCPStreamableHTTPTool,
    Message,
    WorkflowEvent,
)
from agent_framework.openai import OpenAIChatClient
from agent_framework_durabletask import (
    DurableAIAgentOrchestrationContext,
    DurableAIAgentWorker,
)

from fraud_analysis_workflow import (
    SuspiciousActivityAlert,
    FraudRiskAssessment,
    create_fraud_analysis_workflow,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
if _observability_enabled:
    logger.info("✅ Application Insights observability enabled for fraud workflow worker")

# Constants
FRAUD_AGENT_NAME = "FraudAnalysisAgent"
ANALYST_APPROVAL_EVENT = "AnalystDecision"


# ============================================================================
# FraudAnalysisAgent - Custom agent wrapping the inner workflow
# ============================================================================


class FraudAnalysisAgent(BaseAgent):
    """Custom agent that runs the fraud analysis workflow as a DTS entity.

    Registered via DurableAIAgentWorker as entity 'dafx-FraudAnalysisAgent'.
    The entity persists conversation history (DurableAgentState), enabling
    stateful re-investigation when analyst provides feedback.

    Each invocation creates fresh MCP connections (event-loop safe for DTS
    entities which use asyncio.run() per call).
    """

    def __init__(self, *, name: str = FRAUD_AGENT_NAME):
        super().__init__(
            name=name,
            description="Fraud analysis agent with fan-out workflow topology and MCP tools",
        )
        self._mcp_uri = os.getenv("MCP_SERVER_URI", "http://localhost:8000/mcp")
        self._deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    async def run(self, messages: Any = None, *, stream: bool = False, **kwargs: Any) -> AgentResponse:
        """Run fraud analysis. Entity calls this with conversation history.

        On first call: messages contain the alert JSON.
        On subsequent calls (re-investigation): messages contain full history
        including previous analysis and analyst feedback.
        """
        if stream:
            # DTS entity always tries stream=True first, then falls back.
            # Raise TypeError with "stream" in message so entity falls back cleanly.
            raise TypeError("stream=True not supported by FraudAnalysisAgent")

        msg_list: list[Message] = messages if isinstance(messages, list) else []
        alert_data, previous_context = self._parse_messages(msg_list)

        if alert_data is None:
            raise ValueError("No alert data found in messages")

        logger.info(f"[FraudAnalysisAgent] Running analysis for alert {alert_data.get('alert_id')}")
        if previous_context:
            logger.info("[FraudAnalysisAgent] Re-investigation with analyst feedback")

        # Create fresh MCP connection for this event loop (DTS entity uses asyncio.run())
        mcp_tool = MCPStreamableHTTPTool(name="contoso_mcp", url=self._mcp_uri, timeout=30)
        async with mcp_tool:
            # Create chat client
            azure_client_id = os.getenv("AZURE_CLIENT_ID")
            credential = (
                ManagedIdentityCredential(client_id=azure_client_id)
                if azure_client_id
                else DefaultAzureCredential()
            )
            chat_client = OpenAIChatClient(
                credential=credential,
                model=self._deployment_name,
            )

            # If re-investigating, enrich the alert description with previous context
            alert = SuspiciousActivityAlert(**alert_data)
            if previous_context:
                alert = alert.model_copy(update={
                    "description": (
                        f"{alert.description}\n\n"
                        f"--- RE-INVESTIGATION CONTEXT ---\n{previous_context}"
                    ),
                })

            # Build and run the fan-out workflow
            workflow = create_fraud_analysis_workflow(mcp_tool, chat_client)
            assessment: FraudRiskAssessment | None = None

            async for event in workflow.run(alert, stream=True):
                if isinstance(event, WorkflowEvent) and event.type == "output":
                    if isinstance(event.data, FraudRiskAssessment):
                        assessment = event.data
                        break

            if assessment is None:
                raise ValueError("Workflow did not produce FraudRiskAssessment")

            # Add customer_id from original alert
            assessment_dict = assessment.model_dump()
            assessment_dict["customer_id"] = alert_data.get("customer_id", 0)

            logger.info(
                f"[FraudAnalysisAgent] Analysis complete: "
                f"risk={assessment.overall_risk_score:.2f}, action={assessment.recommended_action}"
            )

            # Return as AgentResponse so entity can persist in DurableAgentState
            response_text = json.dumps(assessment_dict, indent=2)
            return AgentResponse(
                messages=[Message(role="assistant", contents=[Content.from_text(response_text)])],
            )

    def _parse_messages(self, messages: list[Message]) -> tuple[dict | None, str | None]:
        """Extract alert data and previous context from entity conversation history.

        Returns:
            (alert_data, previous_context) - alert_data is the original alert dict,
            previous_context is a string with previous findings + analyst feedback.
        """
        alert_data: dict | None = None
        context_parts: list[str] = []

        for msg in messages:
            # Extract text from message
            text = ""
            if hasattr(msg, "text") and msg.text:
                text = msg.text
            elif hasattr(msg, "contents"):
                for c in msg.contents:
                    if hasattr(c, "text") and c.text:
                        text += c.text

            if not text:
                continue

            role = getattr(msg, "role", "")

            if role == "user":
                if alert_data is None:
                    # First user message = alert JSON
                    try:
                        alert_data = json.loads(text)
                    except json.JSONDecodeError:
                        alert_data = None
                else:
                    # Subsequent user messages = analyst feedback
                    context_parts.append(f"ANALYST FEEDBACK: {text}")
            elif role == "assistant" and alert_data is not None:
                # Previous analysis response
                context_parts.append(f"PREVIOUS ANALYSIS:\n{text[:2000]}")

        return alert_data, "\n\n".join(context_parts) if context_parts else None


# ============================================================================
# Input/Output Models
# ============================================================================


class FraudDetectionInput(BaseModel):
    """Input for the fraud detection orchestration."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str = ""
    timestamp: str = ""
    severity: str = "medium"
    approval_timeout_hours: float = 72.0
    max_review_attempts: int = 3


class AnalystDecision(BaseModel):
    """Human analyst decision - supports approve, reject with feedback, or timeout."""
    alert_id: str
    approved: bool  # True = approve action, False = reject and request re-investigation
    approved_action: str = "clear"  # "lock_account", "refund_charges", "clear", "both"
    feedback: str = ""  # Analyst feedback for re-investigation (when approved=False)
    analyst_notes: str = ""
    analyst_id: str = "analyst"


class ActionResult(BaseModel):
    """Result from fraud action execution."""
    alert_id: str
    action_taken: str
    success: bool
    details: str


# ============================================================================
# Activity Functions
# ============================================================================


def notify_analyst(context: ActivityContext, assessment_text: str) -> str:
    """Activity to notify analyst for review."""
    try:
        assessment = json.loads(assessment_text)
        alert_id = assessment.get("alert_id", "unknown")
        risk_score = assessment.get("overall_risk_score", 0)
        recommended = assessment.get("recommended_action", "unknown")
    except (json.JSONDecodeError, AttributeError):
        alert_id = "unknown"
        risk_score = 0
        recommended = "unknown"

    logger.info(f"[Activity] NOTIFICATION: Analyst review required for alert {alert_id}")
    logger.info(f"[Activity] Risk Score: {risk_score}, Recommended: {recommended}")

    return f"Analyst notified for alert {alert_id}"


def execute_fraud_action(context: ActivityContext, decision_dict: dict) -> dict:
    """Activity to execute the approved fraud action."""
    alert_id = decision_dict.get("alert_id", "unknown")
    action = decision_dict.get("approved_action", "unknown")
    analyst_id = decision_dict.get("analyst_id", "unknown")

    logger.info(f"[Activity] Executing fraud action: {action} for alert {alert_id}")
    logger.info(f"[Activity] Approved by analyst: {analyst_id}")

    if action == "lock_account":
        logger.info(f"[Activity] 🔒 Account locked for alert {alert_id}")
    elif action == "refund_charges":
        logger.info(f"[Activity] 💰 Charges refunded for alert {alert_id}")
    elif action == "both":
        logger.info(f"[Activity] 🔒💰 Account locked and charges refunded for alert {alert_id}")
    elif action == "clear":
        logger.info(f"[Activity] ✅ Alert cleared for {alert_id}")

    return ActionResult(
        alert_id=alert_id,
        action_taken=action,
        success=True,
        details=f"Action '{action}' executed successfully",
    ).model_dump()


def auto_clear_alert(context: ActivityContext, assessment_text: str) -> dict:
    """Activity to auto-clear low-risk alerts."""
    try:
        assessment = json.loads(assessment_text)
        alert_id = assessment.get("alert_id", "unknown")
        risk_score = assessment.get("overall_risk_score", 0)
    except (json.JSONDecodeError, AttributeError):
        alert_id = "unknown"
        risk_score = 0

    logger.info(f"[Activity] Auto-clearing low-risk alert {alert_id} (risk={risk_score})")

    return ActionResult(
        alert_id=alert_id,
        action_taken="auto_clear",
        success=True,
        details=f"Alert auto-cleared due to low risk score ({risk_score})",
    ).model_dump()


def escalate_timeout(context: ActivityContext, assessment_text: str) -> dict:
    """Activity to escalate when analyst review times out."""
    try:
        assessment = json.loads(assessment_text)
        alert_id = assessment.get("alert_id", "unknown")
    except (json.JSONDecodeError, AttributeError):
        alert_id = "unknown"

    logger.warning(f"[Activity] ⚠️ ESCALATION: Analyst review timed out for alert {alert_id}")

    return ActionResult(
        alert_id=alert_id,
        action_taken="escalate_timeout",
        success=True,
        details="Escalated to fraud manager due to review timeout",
    ).model_dump()


def send_notification(context: ActivityContext, result_dict: dict) -> str:
    """Activity to send final notification."""
    alert_id = result_dict.get("alert_id", "unknown")
    action_taken = result_dict.get("action_taken", "unknown")

    logger.info(f"[Activity] Sending final notification for alert {alert_id}")
    logger.info(f"[Activity] Action taken: {action_taken}")

    return f"Notification sent for alert {alert_id}, action: {action_taken}"


# ============================================================================
# Main Orchestration (uses DurableAIAgentOrchestrationContext)
# ============================================================================


def fraud_detection_orchestration(
    context: OrchestrationContext,
    payload_raw: Any,
) -> Generator[Task[Any], Any, dict]:
    """Main DTS orchestration for fraud detection with stateful HITL feedback loop.

    This orchestration demonstrates:
    1. DurableAIAgentOrchestrationContext for type-safe agent calls
    2. DurableAgentState for persistent conversation history across iterations
    3. Stateful feedback loop: analyst reject -> re-investigation with full context
    4. External events (HITL), timeouts, activity functions

    Flow:
    1. Call FraudAnalysisAgent entity (inner workflow: fan-out -> aggregate)
    2. Route based on risk score
    3. HIGH RISK: notify analyst -> wait for decision
       - Approve -> execute action -> done
       - Reject + feedback -> re-investigate (same session = stateful) -> loop
       - Timeout -> escalate
    4. LOW RISK: auto-clear
    5. Send notification
    """
    logger.info("[Orchestration] Starting fraud detection orchestration")

    # Validate input
    if not isinstance(payload_raw, dict):
        raise ValueError("Alert data is required")
    try:
        payload = FraudDetectionInput.model_validate(payload_raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid alert input: {exc}") from exc

    alert_id = payload.alert_id
    logger.info(f"[Orchestration] Processing alert {alert_id}")

    # ========================================================================
    # Set up DurableAIAgentOrchestrationContext for agent entity calls
    # ========================================================================

    agent_ctx = DurableAIAgentOrchestrationContext(context)
    fraud_agent = agent_ctx.get_agent(FRAUD_AGENT_NAME)
    fraud_session = fraud_agent.create_session()

    logger.info(f"[Orchestration] Created agent session: {fraud_session.session_id}")

    # ========================================================================
    # Step 1: Initial fraud analysis via DurableAIAgent entity
    # ========================================================================

    alert_json = json.dumps({
        "alert_id": payload.alert_id,
        "customer_id": payload.customer_id,
        "alert_type": payload.alert_type,
        "description": payload.description,
        "timestamp": payload.timestamp,
        "severity": payload.severity,
    })

    context.set_custom_status(json.dumps({
        "message": f"Running fraud analysis for {alert_id}",
        "step_details": {},
        "risk_score": None,
    }))

    logger.info("[Orchestration] Step 1: Running fraud analysis via agent entity...")

    response: AgentResponse = yield fraud_agent.run(
        messages=alert_json,
        session=fraud_session,
    )

    # Parse assessment from agent response
    assessment = json.loads(response.text)
    risk_score = assessment.get("overall_risk_score", 0)
    step_details = assessment.get("step_details", {})

    logger.info(f"[Orchestration] Analysis complete: risk={risk_score:.2f}")

    # ========================================================================
    # Step 2: Route based on risk score with HITL feedback loop
    # ========================================================================

    result: dict
    attempt = 0

    if risk_score >= 0.6:
        # HIGH RISK - Human-in-the-loop with feedback loop
        while attempt < payload.max_review_attempts:
            attempt += 1
            logger.info(
                f"[Orchestration] HIGH RISK ({risk_score:.2f}) - "
                f"Analyst review (attempt {attempt}/{payload.max_review_attempts})"
            )

            context.set_custom_status(json.dumps({
                "message": f"Awaiting analyst review (risk={risk_score:.2f}, attempt {attempt})",
                "step_details": step_details,
                "risk_score": risk_score,
            }))

            # Notify analyst
            yield context.call_activity("notify_analyst", input=response.text)

            # Wait for analyst decision OR timeout
            approval_task: Task[Any] = context.wait_for_external_event(ANALYST_APPROVAL_EVENT)
            timeout_task: Task[Any] = context.create_timer(
                context.current_utc_datetime + timedelta(hours=payload.approval_timeout_hours)
            )

            logger.info(f"[Orchestration] Waiting for analyst decision (timeout: {payload.approval_timeout_hours}h)")
            winner_task = yield when_any([approval_task, timeout_task])

            if winner_task == approval_task:
                # Analyst responded
                decision_data: Any = approval_task.get_result()
                logger.info(f"[Orchestration] Received analyst decision: {decision_data}")

                # Parse decision
                if isinstance(decision_data, dict):
                    decision = AnalystDecision.model_validate(decision_data)
                else:
                    decision = AnalystDecision(
                        alert_id=alert_id,
                        approved=True,
                        approved_action=str(decision_data),
                    )

                if decision.approved:
                    # ====================================================
                    # APPROVED: Execute the action
                    # ====================================================
                    logger.info(f"[Orchestration] ✅ Analyst approved: {decision.approved_action}")

                    step_details["review_gateway"] = {
                        "status": "completed",
                        "tool_calls": [{
                            "name": "analyst_decision",
                            "arguments": {"action": decision.approved_action},
                            "result": f"Approved by {decision.analyst_id}"
                        }],
                        "output": f"Action approved: {decision.approved_action}",
                    }

                    context.set_custom_status(json.dumps({
                        "message": "Executing analyst-approved action",
                        "step_details": step_details,
                        "risk_score": risk_score,
                    }))

                    action_result: dict = yield context.call_activity(
                        "execute_fraud_action",
                        input=decision.model_dump(),
                    )
                    result = action_result

                    step_details["fraud_action_executor"] = {
                        "status": "completed",
                        "tool_calls": [{
                            "name": "execute_fraud_action",
                            "arguments": {"action": decision.approved_action},
                            "result": f"Executed: {result.get('action_taken')}"
                        }],
                        "output": result.get("details", "Action executed"),
                    }
                    break  # Exit the HITL loop

                else:
                    # ====================================================
                    # REJECTED: Re-investigate with feedback (SAME SESSION)
                    # ====================================================
                    feedback = decision.feedback or decision.analyst_notes or "No specific feedback"
                    logger.info(f"[Orchestration] ❌ Analyst rejected. Feedback: {feedback}")

                    if attempt >= payload.max_review_attempts:
                        logger.warning("[Orchestration] Max review attempts exhausted")
                        step_details["review_gateway"] = {
                            "status": "completed",
                            "output": f"Max attempts ({payload.max_review_attempts}) exhausted",
                        }
                        result = ActionResult(
                            alert_id=alert_id,
                            action_taken="max_attempts_exhausted",
                            success=False,
                            details=f"Could not resolve after {payload.max_review_attempts} reviews",
                        ).model_dump()
                        break

                    step_details["review_gateway"] = {
                        "status": "rejected",
                        "tool_calls": [{
                            "name": "analyst_decision",
                            "arguments": {"feedback": feedback},
                            "result": f"Rejected by {decision.analyst_id}: {feedback}"
                        }],
                        "output": f"Rejected - re-investigating (attempt {attempt + 1})",
                    }

                    context.set_custom_status(json.dumps({
                        "message": f"Re-investigating with analyst feedback (attempt {attempt + 1})",
                        "step_details": step_details,
                        "risk_score": risk_score,
                    }))

                    # *** STATEFUL RE-INVESTIGATION ***
                    # Same session -> entity retains full conversation history
                    # Agent sees: original alert + first analysis + feedback
                    feedback_msg = (
                        f"The analyst REJECTED the previous assessment and requests re-investigation.\n"
                        f"Analyst feedback: {feedback}\n"
                        f"Please conduct a deeper investigation focusing on the analyst's concerns."
                    )

                    logger.info("[Orchestration] Re-running fraud analysis with feedback context...")

                    response = yield fraud_agent.run(
                        messages=feedback_msg,
                        session=fraud_session,  # SAME SESSION = stateful!
                    )

                    # Parse updated assessment
                    assessment = json.loads(response.text)
                    risk_score = assessment.get("overall_risk_score", 0)
                    step_details = assessment.get("step_details", {})

                    logger.info(f"[Orchestration] Re-investigation complete: risk={risk_score:.2f}")
                    continue  # Loop back for another review

            else:
                # Timeout - escalate
                logger.warning("[Orchestration] Analyst review timed out")
                context.set_custom_status(json.dumps({
                    "message": "Review timed out - escalating",
                    "step_details": step_details,
                    "risk_score": risk_score,
                }))

                escalation_result: dict = yield context.call_activity(
                    "escalate_timeout", input=response.text
                )
                result = escalation_result
                break

        else:
            # while loop exhausted without break (safety fallback)
            result = ActionResult(
                alert_id=alert_id,
                action_taken="max_attempts_exhausted",
                success=False,
                details="Review loop exhausted",
            ).model_dump()

    else:
        # LOW RISK - Auto-clear
        logger.info(f"[Orchestration] LOW RISK ({risk_score:.2f}) - Auto-clearing")
        context.set_custom_status(json.dumps({
            "message": f"Auto-clearing alert (risk={risk_score:.2f})",
            "step_details": step_details,
            "risk_score": risk_score,
        }))

        clear_result: dict = yield context.call_activity(
            "auto_clear_alert", input=response.text
        )
        result = clear_result

        step_details["auto_clear_executor"] = {
            "status": "completed",
            "output": result.get("details", "Auto-cleared"),
        }

    # ========================================================================
    # Step 3: Send final notification
    # ========================================================================

    logger.info("[Orchestration] Step 3: Sending final notification")
    context.set_custom_status(json.dumps({
        "message": "Sending notification",
        "step_details": step_details,
        "risk_score": risk_score,
    }))

    yield context.call_activity("send_notification", input=result)

    # ========================================================================
    # Complete
    # ========================================================================

    logger.info(f"[Orchestration] ✅ Fraud detection completed for alert {alert_id}")
    context.set_custom_status(json.dumps({
        "message": "Completed",
        "step_details": step_details,
        "risk_score": risk_score,
    }))

    return {
        "alert_id": alert_id,
        "status": "completed",
        "risk_score": risk_score,
        "action_taken": result.get("action_taken"),
        "success": result.get("success"),
        "review_attempts": attempt,
        "step_details": step_details,
    }


# ============================================================================
# Worker Setup
# ============================================================================


def get_worker(
    taskhub: str | None = None,
    endpoint: str | None = None,
) -> DurableTaskSchedulerWorker:
    """Create a configured DurableTaskSchedulerWorker."""
    taskhub_name = taskhub or os.getenv("DTS_TASKHUB", "default")
    endpoint_url = endpoint or os.getenv("DTS_ENDPOINT", "http://localhost:8080")

    logger.info(f"Using DTS endpoint: {endpoint_url}")
    logger.info(f"Using taskhub: {taskhub_name}")

    credential = None if endpoint_url.startswith("http://localhost") else DefaultAzureCredential()

    return DurableTaskSchedulerWorker(
        host_address=endpoint_url,
        secure_channel=not endpoint_url.startswith("http://localhost"),
        taskhub=taskhub_name,
        token_credential=credential,
    )


def setup_worker(worker: DurableTaskSchedulerWorker) -> DurableAIAgentWorker:
    """Set up the worker with agents, orchestrations, and activities.

    Returns:
        DurableAIAgentWorker with agents registered
    """
    # Wrap raw worker with DurableAIAgentWorker for agent entity registration
    agent_worker = DurableAIAgentWorker(worker)

    # Register FraudAnalysisAgent as a durable entity (dafx-FraudAnalysisAgent)
    logger.info("Registering FraudAnalysisAgent as durable entity...")
    fraud_agent = FraudAnalysisAgent()
    agent_worker.add_agent(fraud_agent)
    logger.info(f"✓ Registered entity: dafx-{fraud_agent.name}")

    # Register activity functions on the raw worker
    logger.info("Registering activities...")
    worker.add_activity(notify_analyst)
    worker.add_activity(execute_fraud_action)
    worker.add_activity(auto_clear_alert)
    worker.add_activity(escalate_timeout)
    worker.add_activity(send_notification)
    logger.info("✓ Activities registered")

    # Register the orchestration on the raw worker
    logger.info("Registering orchestration...")
    worker.add_orchestrator(fraud_detection_orchestration)
    logger.info("✓ Orchestration registered")

    return agent_worker


async def main():
    """Main entry point for the worker process."""
    logger.info("=" * 60)
    logger.info("Starting Durable Fraud Detection Worker")
    logger.info("  Architecture: DurableAIAgentWorker + Workflow + HITL")
    logger.info("=" * 60)

    # Create and setup worker
    worker = get_worker()
    agent_worker = setup_worker(worker)

    logger.info("")
    logger.info(f"Registered agents: {agent_worker.registered_agent_names}")
    logger.info("Worker is ready and listening for orchestrations!")
    logger.info("Dashboard: http://localhost:8082")
    logger.info("Press Ctrl+C to stop.")
    logger.info("")

    try:
        worker.start()

        # Keep running — use threading.Event for Windows compatibility.
        # asyncio.sleep() can be cancelled by gRPC's SIGINT handler on Windows,
        # so we fall back to a thread-safe wait.
        import threading
        stop_event = threading.Event()
        try:
            while not stop_event.wait(timeout=1):
                pass
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
    except KeyboardInterrupt:
        logger.info("Worker shutdown initiated")
    finally:
        # Gracefully stop the worker to tear down gRPC channels.
        # Without this, the gRPC C-extension thread can keep the process
        # alive indefinitely even after the Python runtime shuts down.
        try:
            worker.stop()
        except Exception:
            pass

    logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
