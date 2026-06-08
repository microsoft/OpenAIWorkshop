"""
FastAPI Backend for Durable Fraud Detection.

This backend provides:
1. REST API to start orchestrations and submit decisions
2. WebSocket for real-time status updates
3. Integration with DTS client

The UI connects here instead of managing workflow directly.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

from pathlib import Path

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
# Add parent directories to path for the shared observability module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # agentic_ai/

_observability_enabled = False
if os.getenv("BACKEND_OBSERVABILITY", "false").lower() in ("1", "true", "yes"):
    try:
        from observability import setup_observability
        _observability_enabled = setup_observability(
            service_name="contoso-fraud-workflow",
            enable_live_metrics=True,
            enable_sensitive_data=os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() in ("1", "true", "yes"),
        )
    except (ImportError, Exception):
        _observability_enabled = False

# ------------------------------------------------------------------
from azure.identity import DefaultAzureCredential
from durabletask.azuremanaged.client import DurableTaskSchedulerClient
from durabletask.client import OrchestrationState
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from event_producer import EventProducer, CUSTOMER_PROFILES, TelemetryEvent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
if _observability_enabled:
    logger.info("✅ Application Insights observability enabled for fraud workflow backend")

# FastAPI app
app = FastAPI(
    title="Durable Fraud Detection API",
    description="Hybrid Workflow + Durable Task architecture for fraud detection",
    version="1.0.0",
)

# CORS - allow localhost for dev and Azure Container Apps for prod
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8001",
    "http://localhost:8002",
]
# Add Azure Container Apps URL if set
if os.getenv("CONTAINER_APP_URL"):
    CORS_ORIGINS.append(os.getenv("CONTAINER_APP_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Static Files (React UI)
# ============================================================================

# Serve static files from React build (production mode)
# Vite outputs to 'dist/' with assets in 'dist/assets/'
STATIC_DIR = Path(__file__).parent / "static"
STATIC_ASSET_DIR = STATIC_DIR / "assets"  # Vite structure

if STATIC_ASSET_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_ASSET_DIR)), name="assets")
    logger.info(f"Serving static assets from {STATIC_ASSET_DIR}")
elif STATIC_DIR.exists():
    # Fallback: mount entire static dir
    logger.info(f"Static assets dir not found, mounting {STATIC_DIR}")

# Constants
ANALYST_APPROVAL_EVENT = "AnalystDecision"
ORCHESTRATION_NAME = "fraud_detection_orchestration"


# ============================================================================
# Request/Response Models
# ============================================================================


class StartWorkflowRequest(BaseModel):
    """Request to start a fraud detection workflow."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str = ""
    severity: str = "medium"
    approval_timeout_hours: float = 72.0


class StartWorkflowResponse(BaseModel):
    """Response after starting a workflow."""
    instance_id: str
    alert_id: str
    status: str


class AnalystDecisionRequest(BaseModel):
    """Analyst decision submitted from UI."""
    instance_id: str
    alert_id: str
    approved: bool = True  # True = approve action, False = reject with feedback
    approved_action: str = "clear"
    feedback: str = ""  # Feedback for re-investigation (when approved=False)
    analyst_notes: str = ""
    analyst_id: str = "analyst_ui"


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    instance_id: str
    status: str
    custom_status: str | None
    result: dict | None


class AlertInfo(BaseModel):
    """Sample alert info."""
    alert_id: str
    customer_id: int
    alert_type: str
    description: str
    severity: str


# ============================================================================
# Sample Alerts
# ============================================================================

SAMPLE_ALERTS = [
    AlertInfo(
        alert_id="ALERT-001",
        customer_id=1,
        alert_type="multi_country_login",
        description="Login attempts from USA and Russia within 2 hours",
        severity="high",
    ),
    AlertInfo(
        alert_id="ALERT-002",
        customer_id=2,
        alert_type="data_spike",
        description="Data usage increased by 500% in last 24 hours",
        severity="medium",
    ),
    AlertInfo(
        alert_id="ALERT-003",
        customer_id=3,
        alert_type="unusual_charges",
        description="Three large purchases totaling $5,000 in 10 minutes",
        severity="high",
    ),
]


# ============================================================================
# DTS Client
# ============================================================================

_dts_client: DurableTaskSchedulerClient | None = None


def get_dts_client() -> DurableTaskSchedulerClient:
    """Get or create DTS client."""
    global _dts_client
    
    if _dts_client is None:
        taskhub = os.getenv("DTS_TASKHUB", "default")
        endpoint = os.getenv("DTS_ENDPOINT", "http://localhost:8080")
        
        credential = None if endpoint.startswith("http://localhost") else DefaultAzureCredential()
        
        _dts_client = DurableTaskSchedulerClient(
            host_address=endpoint,
            secure_channel=not endpoint.startswith("http://localhost"),
            taskhub=taskhub,
            token_credential=credential,
        )
        logger.info(f"DTS client initialized: {endpoint}/{taskhub}")
    
    return _dts_client


# ============================================================================
# WebSocket Manager
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}  # instance_id -> connections

    async def connect(self, websocket: WebSocket, instance_id: str):
        await websocket.accept()
        if instance_id not in self.active_connections:
            self.active_connections[instance_id] = []
        self.active_connections[instance_id].append(websocket)
        logger.info(f"WebSocket connected for instance {instance_id}")

    def disconnect(self, websocket: WebSocket, instance_id: str):
        if instance_id in self.active_connections:
            self.active_connections[instance_id].remove(websocket)
            if not self.active_connections[instance_id]:
                del self.active_connections[instance_id]
        logger.info(f"WebSocket disconnected for instance {instance_id}")

    async def broadcast(self, instance_id: str, message: dict):
        """Broadcast message to all connections watching this instance."""
        if instance_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[instance_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect(conn, instance_id)


manager = ConnectionManager()

# ============================================================================
# Event Producer (Layer 1 — Ambient Detection)
# ============================================================================

event_producer = EventProducer(
    interval_seconds=float(os.getenv("EVENT_INTERVAL_SECONDS", "3.0")),
    anomaly_probability=float(os.getenv("ANOMALY_PROBABILITY", "0.08")),
)
_event_producer_task: asyncio.Task | None = None


async def _auto_submit_alert_callback(alert_id, customer_id, alert_type, description, severity):
    """Auto-submit a detected anomaly (Layer 1) to the durable workflow (Layer 2)."""
    try:
        client = get_dts_client()
        alert = {
            "alert_id": alert_id,
            "customer_id": customer_id,
            "alert_type": alert_type,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "approval_timeout_hours": 0.05,
            "auto_detected": True,
        }
        instance_id = client.schedule_new_orchestration(
            ORCHESTRATION_NAME,
            input=alert,
            instance_id=f"fraud-{alert_id}-{int(time.time())}",
        )
        logger.info(f"🤖 Auto-submitted alert {alert_id} → orchestration {instance_id}")

        started_event = TelemetryEvent(
            id=f"WF-{alert_id}",
            timestamp=alert["timestamp"],
            customer_id=customer_id,
            customer_name=CUSTOMER_PROFILES.get(customer_id, {}).get("name", f"Customer {customer_id}"),
            event_type="workflow_auto_started",
            details={
                "instance_id": instance_id,
                "alert_id": alert_id,
                "alert_type": alert_type,
                "description": description,
                "severity": severity,
            },
            is_anomaly=True,
            anomaly_rule=alert_type,
            alert_triggered=True,
        )
        await event_producer._broadcast(started_event)
    except Exception as e:
        logger.error(f"Failed to auto-submit alert: {e}")


def _start_event_producer() -> bool:
    """Start the ambient event producer if not already running. Returns running state."""
    global _event_producer_task
    if _event_producer_task and not _event_producer_task.done():
        return True
    event_producer.set_alert_callback(_auto_submit_alert_callback)
    _event_producer_task = asyncio.create_task(event_producer.run())
    logger.info("▶ Event producer started (Layer 1 ambient detection)")
    return True


def _stop_event_producer() -> bool:
    """Stop the ambient event producer if running. Returns running state."""
    global _event_producer_task
    event_producer.stop()
    if _event_producer_task:
        _event_producer_task.cancel()
        _event_producer_task = None
    logger.info("⏸ Event producer stopped")
    return False


def _event_producer_running() -> bool:
    return bool(_event_producer_task and not _event_producer_task.done())


# ============================================================================
# Background Task: Poll DTS for Status Updates
# ============================================================================

_polling_tasks: dict[str, asyncio.Task] = {}


async def poll_orchestration_status(instance_id: str):
    """Background task to poll DTS and broadcast status updates."""
    client = get_dts_client()
    last_status = None
    last_custom_status = None
    
    while instance_id in manager.active_connections:
        try:
            state = client.get_orchestration_state(instance_id)
            
            if state:
                status = state.runtime_status.name
                custom_status_raw = state.serialized_custom_status
                
                # Debug: log raw custom_status
                # logger.info(f"[Backend] Raw custom_status: {custom_status_raw[:200] if custom_status_raw else 'None'}")
                
                # Parse custom_status JSON if present
                custom_status = custom_status_raw
                step_details = None
                status_message = custom_status_raw
                
                if custom_status_raw:
                    try:
                        parsed = json.loads(custom_status_raw)
                        # Handle double-encoding: if parsed is still a string, parse again
                        if isinstance(parsed, str):
                            try:
                                parsed = json.loads(parsed)
                            except json.JSONDecodeError:
                                pass  # Keep as string
                        
                        if isinstance(parsed, dict):
                            status_message = parsed.get("message", custom_status_raw)
                            step_details = parsed.get("step_details")
                            custom_status = status_message
                    except json.JSONDecodeError:
                        pass  # Keep original string
                
                # Only broadcast if status changed
                if status != last_status or custom_status_raw != last_custom_status:
                    message = {
                        "type": "status_update",
                        "instance_id": instance_id,
                        "status": status,
                        "custom_status": custom_status,
                        "step_details": step_details,
                        "timestamp": datetime.now().isoformat(),
                    }
                    
                    # Check if waiting for analyst
                    if custom_status and "Awaiting analyst" in custom_status:
                        message["decision_required"] = True
                    
                    # Check if completed
                    if status in ("COMPLETED", "FAILED", "TERMINATED"):
                        if state.serialized_output:
                            try:
                                message["result"] = json.loads(state.serialized_output)
                            except json.JSONDecodeError:
                                message["result"] = {"raw": state.serialized_output}
                    
                    await manager.broadcast(instance_id, message)
                    
                    last_status = status
                    last_custom_status = custom_status_raw
                
                # Stop polling if completed
                if status in ("COMPLETED", "FAILED", "TERMINATED"):
                    logger.info(f"Orchestration {instance_id} completed, stopping poll")
                    break
        
        except Exception as e:
            logger.error(f"Error polling status for {instance_id}: {e}")
        
        await asyncio.sleep(0.1)  # Poll every 100ms for responsive UI
    
    # Cleanup
    if instance_id in _polling_tasks:
        del _polling_tasks[instance_id]


def start_status_polling(instance_id: str):
    """Start background polling for an instance."""
    if instance_id not in _polling_tasks:
        task = asyncio.create_task(poll_orchestration_status(instance_id))
        _polling_tasks[instance_id] = task


# ============================================================================
# REST API Endpoints
# ============================================================================


@app.get("/")
async def read_root():
    """Serve the React frontend index.html."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "Durable Fraud Detection API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Deep readiness check.

    Verifies the three external dependencies the demo needs so a presenter can
    confirm everything is wired *before* starting a scenario:
      - DTS      : can we reach the Durable Task Scheduler taskhub?
      - MCP      : is the Contoso MCP server responding?
      - OpenAI   : can DefaultAzureCredential acquire a token (Entra auth)?

    Returns 200 when all checks pass, 503 otherwise. Each check is best-effort
    and time-boxed so the endpoint stays fast and never hangs the UI.
    """
    checks: dict[str, dict] = {}

    # 1) DTS connectivity — a metadata lookup on a non-existent instance returns
    #    None when the gRPC channel + auth are healthy.
    try:
        client = get_dts_client()
        await asyncio.wait_for(
            asyncio.to_thread(client.get_orchestration_state, "health-check-probe"),
            timeout=5.0,
        )
        checks["dts"] = {"ok": True, "endpoint": os.getenv("DTS_ENDPOINT", "http://localhost:8080")}
    except Exception as e:
        checks["dts"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # 2) MCP server reachability. FastMCP serves only the /mcp endpoint (no
    #    /health route), and that endpoint expects specific POST semantics, so
    #    we verify reachability with a lightweight TCP connect to host:port.
    mcp_uri = os.getenv("MCP_SERVER_URI", "http://localhost:8000/mcp")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(mcp_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=5.0)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        checks["mcp"] = {"ok": True, "host": host, "port": port}
    except Exception as e:
        checks["mcp"] = {"ok": False, "error": f"{type(e).__name__}: {e}", "uri": mcp_uri}

    # 3) Azure OpenAI auth — can we get an Entra token for the cognitive
    #    services scope? (The worker/backend authenticate via DefaultAzureCredential.)
    try:
        cred = DefaultAzureCredential()
        token = await asyncio.wait_for(
            asyncio.to_thread(cred.get_token, "https://cognitiveservices.azure.com/.default"),
            timeout=5.0,
        )
        checks["openai_auth"] = {"ok": bool(token and token.token)}
    except Exception as e:
        checks["openai_auth"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    healthy = all(c.get("ok") for c in checks.values())
    body = {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }
    if not healthy:
        return JSONResponse(status_code=503, content=body)
    return body


@app.get("/api/producer/status")
async def producer_status():
    """Return whether the ambient event producer is running."""
    return {
        "running": _event_producer_running(),
        "interval_seconds": event_producer.interval,
        "anomaly_probability": event_producer.anomaly_probability,
    }


@app.post("/api/producer/start")
async def producer_start():
    """Start the ambient event producer (Layer 1 detection feed)."""
    running = _start_event_producer()
    return {"running": running}


@app.post("/api/producer/stop")
async def producer_stop():
    """Stop the ambient event producer."""
    running = _stop_event_producer()
    return {"running": running}


@app.get("/api/alerts", response_model=list[AlertInfo])
async def get_alerts():
    """Get sample alerts."""
    return SAMPLE_ALERTS


@app.post("/api/workflow/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest):
    """Start a new fraud detection orchestration."""
    client = get_dts_client()
    
    alert = {
        "alert_id": request.alert_id,
        "customer_id": request.customer_id,
        "alert_type": request.alert_type,
        "description": request.description,
        "timestamp": datetime.now().isoformat(),
        "severity": request.severity,
        "approval_timeout_hours": request.approval_timeout_hours,
    }
    
    instance_id = client.schedule_new_orchestration(
        ORCHESTRATION_NAME,
        input=alert,
        instance_id=f"fraud-{request.alert_id}-{int(time.time())}",
    )
    
    logger.info(f"Started orchestration {instance_id} for alert {request.alert_id}")
    
    return StartWorkflowResponse(
        instance_id=instance_id,
        alert_id=request.alert_id,
        status="started",
    )


@app.get("/api/workflow/status/{instance_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(instance_id: str):
    """Get current status of an orchestration."""
    client = get_dts_client()
    
    state = client.get_orchestration_state(instance_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Orchestration not found")
    
    result = None
    if state.serialized_output:
        try:
            result = json.loads(state.serialized_output)
        except json.JSONDecodeError:
            result = {"raw": state.serialized_output}
    
    return WorkflowStatusResponse(
        instance_id=instance_id,
        status=state.runtime_status.name,
        custom_status=state.serialized_custom_status,
        result=result,
    )


@app.post("/api/workflow/decision")
async def submit_decision(request: AnalystDecisionRequest):
    """Submit analyst decision for a pending orchestration."""
    client = get_dts_client()
    
    decision = {
        "alert_id": request.alert_id,
        "approved": request.approved,
        "approved_action": request.approved_action,
        "feedback": request.feedback,
        "analyst_notes": request.analyst_notes,
        "analyst_id": request.analyst_id,
    }
    
    client.raise_orchestration_event(
        instance_id=request.instance_id,
        event_name=ANALYST_APPROVAL_EVENT,
        data=decision,
    )
    
    logger.info(f"Submitted decision for {request.instance_id}: {request.approved_action}")
    
    # Broadcast decision event
    await manager.broadcast(request.instance_id, {
        "type": "decision_submitted",
        "instance_id": request.instance_id,
        "action": request.approved_action,
        "timestamp": datetime.now().isoformat(),
    })
    
    return {"status": "submitted", "instance_id": request.instance_id}


# ============================================================================
# SSE Endpoint — Live Event Feed (Layer 1 → UI)
# ============================================================================


@app.get("/api/events/stream")
async def event_stream():
    """Server-Sent Events stream of live telemetry + anomaly detections.

    The React UI connects here with EventSource to display the Live Feed panel.
    Events are JSON objects with event_type, customer_name, is_anomaly, etc.
    """
    queue = event_producer.subscribe()

    async def generate():
        try:
            while True:
                event = await queue.get()
                data = json.dumps(event.to_dict())
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_producer.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    })


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@app.websocket("/ws/{instance_id}")
async def websocket_endpoint(websocket: WebSocket, instance_id: str):
    """
    WebSocket endpoint for real-time status updates.
    
    Connect to /ws/{instance_id} to receive updates for a specific orchestration.
    """
    await manager.connect(websocket, instance_id)
    
    # Start polling for this instance
    start_status_polling(instance_id)
    
    try:
        # Send initial status
        client = get_dts_client()
        state = client.get_orchestration_state(instance_id)
        
        if state:
            await websocket.send_json({
                "type": "initial_status",
                "instance_id": instance_id,
                "status": state.runtime_status.name,
                "custom_status": state.serialized_custom_status,
            })
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong, commands, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                
                # Handle client commands
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {instance_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {instance_id}: {e}")
    finally:
        manager.disconnect(websocket, instance_id)


# ============================================================================
# Startup/Shutdown
# ============================================================================


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    global _event_producer_task
    
    logger.info("="*60)
    logger.info("Starting Durable Fraud Detection Backend")
    logger.info("="*60)
    
    # DTS client is lazy-initialized on first API call (get_dts_client()).
    # Pre-init inside uvicorn's startup causes a CancelledError on Windows
    # because gRPC's C extension installs a SIGINT handler that conflicts
    # with asyncio's ProactorEventLoop signal handling.
    logger.info("✓ DTS client will initialize on first request (lazy)")
    
    # Start Layer 1 event producer (ambient detection).
    # Default OFF so a presenter controls when the demo's ambient feed begins
    # (use the UI toggle or POST /api/producer/start). Set EVENT_PRODUCER_ENABLED=true
    # to auto-start on boot.
    if os.getenv("EVENT_PRODUCER_ENABLED", "false").lower() in ("1", "true", "yes"):
        _start_event_producer()
        logger.info("✓ Event producer auto-started (EVENT_PRODUCER_ENABLED=true)")
    else:
        logger.info("⏸ Event producer idle — start it from the UI or POST /api/producer/start")
    
    logger.info("Backend ready! 🚀")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down backend...")
    
    # Stop event producer
    event_producer.stop()
    if _event_producer_task:
        _event_producer_task.cancel()
    
    # Cancel polling tasks
    for task in _polling_tasks.values():
        task.cancel()


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("BACKEND_PORT", "8001"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
