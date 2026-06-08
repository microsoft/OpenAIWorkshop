# Copyright (c) Microsoft. All rights reserved.

"""
Observability setup for Agent Framework applications with Application Insights.

This module configures OpenTelemetry to send traces, logs, and metrics to 
Azure Application Insights, enabling full observability of agent executions.

Azure Monitor Dashboards (no Grafana required):
    - Agent Overview: https://aka.ms/amg/dash/af-agent
    - Workflow Overview: https://aka.ms/amg/dash/af-workflow

Usage:
    1. Set APPLICATIONINSIGHTS_CONNECTION_STRING in your .env
    2. Call setup_observability() once at app startup
    3. All Agent Framework traces are captured automatically
"""

import os
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track initialization state
_initialized = False


def _ensure_utf8_console() -> None:
    """Force stdout/stderr to UTF-8 so emoji/unicode never crash a print().

    On Windows the default console encoding is cp1252, which raises
    UnicodeEncodeError when printing emoji (✅, ⚠️, 🚀, etc.). Because this
    module is imported at process startup (before any agent output), calling
    this here makes every downstream print()/log safe. Uses errors="replace"
    as a final guard so even an un-encodable glyph degrades gracefully instead
    of crashing the service.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Never let console hardening break startup.
            pass


# Harden the console as soon as this module is imported.
_ensure_utf8_console()


def _safe_print(message: str) -> None:
    """print() that can never raise on un-encodable characters."""
    try:
        print(message)
    except Exception:
        try:
            print(message.encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass


def setup_observability(
    connection_string: Optional[str] = None,
    service_name: str = "contoso-agent",
    enable_live_metrics: bool = True,
    enable_sensitive_data: bool = False,
) -> bool:
    """
    Configure Application Insights for Agent Framework observability.
    
    This follows the pattern from agent-framework/python/samples/getting_started/observability/.
    
    Args:
        connection_string: App Insights connection string (or set APPLICATIONINSIGHTS_CONNECTION_STRING).
        service_name: Service name shown in App Insights.
        enable_live_metrics: Enable Live Metrics stream.
        enable_sensitive_data: Include prompts/responses in traces (dev only!).
    
    Returns:
        True if setup succeeded, False otherwise.
    """
    global _initialized
    
    if _initialized:
        return True
    
    # Get connection string from parameter or environment
    conn_str = connection_string or os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_str:
        logger.debug("No APPLICATIONINSIGHTS_CONNECTION_STRING - observability disabled")
        return False
    
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from agent_framework.observability import create_resource, enable_instrumentation
        
        # Set service name via standard env var
        os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
        
        # Configure Azure Monitor (same pattern as agent-framework samples)
        configure_azure_monitor(
            connection_string=conn_str,
            resource=create_resource(),
            enable_live_metrics=enable_live_metrics,
        )
        
        # Enable Agent Framework instrumentation
        enable_instrumentation(enable_sensitive_data=enable_sensitive_data)
        
        # Workaround: agent_framework._tools.py calls
        # model_dump_json(ensure_ascii=False), but Pydantic v2 doesn't
        # support that kwarg, causing every tool call to fail with
        # "Function failed". Monkeypatch BaseModel.model_dump_json to
        # silently strip unsupported kwargs so observability doesn't
        # break tool execution.  Remove once the library is fixed.
        import pydantic
        _orig_mdj = pydantic.BaseModel.model_dump_json
        def _safe_model_dump_json(self, **kwargs):
            kwargs.pop("ensure_ascii", None)
            return _orig_mdj(self, **kwargs)
        pydantic.BaseModel.model_dump_json = _safe_model_dump_json  # type: ignore[assignment]
        
        _initialized = True
        _safe_print(f"✅ Application Insights observability enabled (service: {service_name})")
        logger.info(f"✅ Application Insights observability enabled (service: {service_name})")
        return True
        
    except ImportError as e:
        _safe_print(f"❌ Observability dependencies not installed: {e}")
        logger.warning(f"Observability dependencies not installed: {e}")
        return False
    except BaseException as e:
        # Catch ALL errors including KeyboardInterrupt from import deadlocks
        # in azure-ai-projects telemetry instrumentor (openai SDK version conflicts).
        # Observability is never worth crashing the service.
        _safe_print(f"⚠️ Observability setup failed (non-fatal): {type(e).__name__}: {e}")
        logger.warning(f"Observability setup failed (non-fatal): {type(e).__name__}: {e}")
        return False


def get_tracer(name: str = "contoso-agent"):
    """Get an OpenTelemetry tracer for creating custom spans."""
    from agent_framework.observability import get_tracer as af_get_tracer
    return af_get_tracer(name)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID for correlation."""
    from opentelemetry import trace
    from opentelemetry.trace.span import format_trace_id
    
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format_trace_id(current_span.get_span_context().trace_id)
    return None
