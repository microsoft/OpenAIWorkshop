"""
Regression tests for agent-framework 1.2.1 upgrade.

Tests all agent types (single, handoff, reflection, magentic) to verify:
1. Import compatibility with the 1.2.1 API
2. Constructor signatures work correctly
3. Session management (AgentSession)
4. Streaming API (run(stream=True))
5. Event processing (unified WorkflowEvent model)
6. MagenticBuilder constructor-based API
7. Native HandoffBuilder integration in the handoff agent
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Ensure the agent packages are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agentic_ai'))


# =============================================================================
# Section 1: Import Compatibility Tests
# =============================================================================


class TestImportCompatibility:
    """Verify all imports resolve correctly against agent-framework 1.2.1."""

    def test_core_framework_imports(self):
        """Core agent_framework symbols used across all agents."""
        from agent_framework import (
            Agent,
            AgentSession,
            ChatOptions,
            MCPStreamableHTTPTool,
            WorkflowCheckpoint,
            WorkflowEvent,
            CheckpointStorage,
            ResponseStream,
            WorkflowRunResult,
            Role,
            Message,
            Content,
        )
        assert Agent is not None
        assert AgentSession is not None
        assert ChatOptions is not None

    def test_openai_client_import(self):
        """OpenAIChatClient is the unified chat client (replaces AzureOpenAIChatClient)."""
        from agent_framework.openai import OpenAIChatClient
        assert OpenAIChatClient is not None

    def test_legacy_azure_client_removed(self):
        """The 1.0.0rc1 AzureOpenAIChatClient is no longer exported by agent_framework.azure."""
        import agent_framework.azure as az
        assert not hasattr(az, "AzureOpenAIChatClient"), (
            "AzureOpenAIChatClient was removed in 1.2.x; use "
            "agent_framework.openai.OpenAIChatClient with azure_endpoint=... instead."
        )

    def test_orchestration_imports(self):
        """Orchestration symbols moved to agent_framework_orchestrations."""
        from agent_framework_orchestrations import (
            MagenticBuilder,
            MagenticOrchestratorEvent,
            MagenticOrchestratorEventType,
            MagenticPlanReviewRequest,
            MagenticPlanReviewResponse,
        )
        assert MagenticBuilder is not None

    def test_native_handoff_imports(self):
        """Native handoff orchestration is available in 1.2.x."""
        from agent_framework_orchestrations import (
            HandoffBuilder,
            HandoffAgentUserRequest,
            HandoffSentEvent,
            HandoffConfiguration,
        )
        assert HandoffBuilder is not None
        assert HandoffSentEvent is not None
        assert HandoffConfiguration is not None
        # HandoffAgentUserRequest provides helpers used by chat_async resumption
        assert hasattr(HandoffAgentUserRequest, "create_response")

    def test_single_agent_import(self):
        """Single agent module loads cleanly."""
        from agents.agent_framework.single_agent import Agent
        assert Agent is not None

    def test_handoff_agent_import(self):
        """Handoff multi-domain agent module loads cleanly."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import Agent
        assert Agent is not None

    def test_reflection_agent_import(self):
        """Reflection agent module loads cleanly."""
        from agents.agent_framework.multi_agent.reflection_agent import Agent
        assert Agent is not None

    def test_magentic_group_import(self):
        """Magentic group agent module loads cleanly."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        assert Agent is not None

    def test_default_agent_export(self):
        """Default agent_framework package re-exports single_agent.Agent."""
        from agents.agent_framework import Agent
        from agents.agent_framework.single_agent import Agent as SingleAgent
        assert Agent is SingleAgent

    def test_old_symbols_removed(self):
        """Verify old symbols (ChatAgent, AgentThread, etc.) are NOT available."""
        import agent_framework
        assert not hasattr(agent_framework, 'ChatAgent'), "ChatAgent should be renamed to Agent"
        assert not hasattr(agent_framework, 'AgentThread'), "AgentThread should be renamed to AgentSession"
        assert not hasattr(agent_framework, 'ChatMessage'), "ChatMessage should be renamed to Message"


# =============================================================================
# Section 2: Agent Constructor Tests
# =============================================================================


class TestAgentConstructors:
    """Verify agent constructors use the 1.2.1 signatures."""

    def test_framework_agent_constructor_signature(self):
        """Agent(client, instructions, *, name, tools, default_options)."""
        from agent_framework import Agent
        import inspect
        sig = inspect.signature(Agent.__init__)
        params = list(sig.parameters.keys())
        # First positional after self should be 'client'
        assert params[1] == 'client', f"First param should be 'client', got {params[1]}"
        assert 'name' in params
        assert 'tools' in params
        assert 'default_options' in params
        # 1.2.x adds first-class support for handoff workflows via this flag
        assert 'require_per_service_call_history_persistence' in params
        # description was wired through in 1.2.x and is consumed by HandoffBuilder
        assert 'description' in params

    def test_chat_options_model_id(self):
        """ChatOptions accepts model_id for specifying the model."""
        from agent_framework import ChatOptions
        opts = ChatOptions(model_id="gpt-4o")
        assert opts["model_id"] == "gpt-4o"

    def test_openai_client_constructor_supports_azure_kwargs(self):
        """OpenAIChatClient accepts model, api_key, credential, azure_endpoint, api_version."""
        from agent_framework.openai import OpenAIChatClient
        import inspect
        sig = inspect.signature(OpenAIChatClient.__init__)
        params = set(sig.parameters.keys()) - {'self'}
        # Unified client uses `model` (not `deployment_name`) and `azure_endpoint` (not `endpoint`)
        assert 'model' in params
        assert 'api_key' in params
        assert 'credential' in params
        assert 'azure_endpoint' in params
        assert 'api_version' in params
        # The legacy 1.0.0rc1 names should not be present anymore
        assert 'deployment_name' not in params, "deployment_name was renamed to model in 1.2.x"

    def test_openai_client_routes_to_azure(self):
        """Passing azure_endpoint routes the OpenAIChatClient to the Azure backend."""
        from agent_framework.openai import OpenAIChatClient
        client = OpenAIChatClient(
            model="gpt-4o",
            api_key="dummy-key",
            azure_endpoint="https://example.openai.azure.com/",
            api_version="2024-08-01-preview",
        )
        assert client.azure_endpoint == "https://example.openai.azure.com/"
        assert client.api_version == "2024-08-01-preview"


# =============================================================================
# Section 3: Session Management Tests (AgentThread → AgentSession)
# =============================================================================


class TestSessionManagement:
    """Verify AgentSession works correctly as the replacement for AgentThread."""

    def test_agent_session_creation(self):
        """AgentSession can be created with default or custom session_id."""
        from agent_framework import AgentSession
        session = AgentSession()
        assert session.session_id is not None
        
        custom = AgentSession(session_id="test-123")
        assert custom.session_id == "test-123"

    def test_agent_session_serialization(self):
        """AgentSession supports to_dict() and from_dict()."""
        from agent_framework import AgentSession
        session = AgentSession(session_id="test-serialize")
        data = session.to_dict()
        assert isinstance(data, dict)
        assert data.get("session_id") == "test-serialize"
        
        restored = AgentSession.from_dict(data)
        assert restored.session_id == "test-serialize"

    def test_agent_has_create_session(self):
        """Agent has create_session() method (replaces get_new_thread)."""
        from agent_framework import Agent
        assert hasattr(Agent, 'create_session')
        assert callable(getattr(Agent, 'create_session'))

    def test_agent_no_old_thread_methods(self):
        """Agent does NOT have old thread methods."""
        from agent_framework import Agent
        assert not hasattr(Agent, 'get_new_thread')
        assert not hasattr(Agent, 'deserialize_thread')
        assert not hasattr(Agent, 'run_stream')


# =============================================================================
# Section 4: Streaming API Tests
# =============================================================================


class TestStreamingAPI:
    """Verify run(stream=True) replaces the old run_stream() method."""

    def test_agent_run_supports_stream_kwarg(self):
        """Agent.run() accepts stream=True."""
        from agent_framework import Agent
        import inspect
        sig = inspect.signature(Agent.run)
        assert 'stream' in sig.parameters

    def test_agent_run_supports_session_kwarg(self):
        """Agent.run() accepts session=... (replaces thread=...)."""
        from agent_framework import Agent
        import inspect
        sig = inspect.signature(Agent.run)
        assert 'session' in sig.parameters

    def test_response_stream_has_updates(self):
        """ResponseStream has .updates property for iteration."""
        from agent_framework import ResponseStream
        assert hasattr(ResponseStream, 'updates')

    def test_agent_response_update_structure(self):
        """AgentResponseUpdate has contents and text."""
        from agent_framework import AgentResponseUpdate
        update = AgentResponseUpdate()
        assert hasattr(update, 'contents')
        assert hasattr(update, 'text')

    def test_content_types(self):
        """Content factory methods exist for function_call and function_result."""
        from agent_framework import Content
        assert hasattr(Content, 'from_function_call')
        assert hasattr(Content, 'from_function_result')
        assert hasattr(Content, 'from_text')


# =============================================================================
# Section 5: Workflow Event Model Tests (Unified WorkflowEvent)
# =============================================================================


class TestWorkflowEventModel:
    """Verify the unified WorkflowEvent replaces old typed event classes."""

    def test_workflow_event_output(self):
        """WorkflowEvent.output() factory creates an output event."""
        from agent_framework import WorkflowEvent
        event = WorkflowEvent.output("executor_1", "final answer")
        assert event.type == "output"
        assert event.executor_id == "executor_1"
        assert event.data == "final answer"

    def test_workflow_event_executor_completed(self):
        """WorkflowEvent.executor_completed() for completed agent responses."""
        from agent_framework import WorkflowEvent
        event = WorkflowEvent.executor_completed("crm_billing", "response text")
        assert event.type == "executor_completed"
        assert event.executor_id == "crm_billing"

    def test_workflow_event_emit(self):
        """WorkflowEvent.emit() for streaming data."""
        from agent_framework import WorkflowEvent
        event = WorkflowEvent.emit("agent_1", "streaming chunk")
        assert event.type == "data"
        assert event.executor_id == "agent_1"

    def test_workflow_event_request_info(self):
        """WorkflowEvent.request_info() for plan reviews."""
        from agent_framework import WorkflowEvent
        event = WorkflowEvent.request_info(
            "req-123", "magentic_manager", "plan data", response_type=str
        )
        assert event.type == "request_info"
        assert event.request_id == "req-123"

    def test_old_event_types_removed(self):
        """Old event types no longer exist in agent_framework."""
        import agent_framework
        for old_type in ['WorkflowOutputEvent', 'AgentRunEvent', 'AgentRunUpdateEvent', 'RequestInfoEvent']:
            assert not hasattr(agent_framework, old_type), f"{old_type} should no longer exist"

    def test_magentic_orchestrator_event_type(self):
        """MagenticOrchestratorEventType enum values."""
        from agent_framework_orchestrations import MagenticOrchestratorEventType
        values = {e.value for e in MagenticOrchestratorEventType}
        assert "plan_created" in values
        assert "replanned" in values
        assert "progress_ledger_updated" in values


# =============================================================================
# Section 6: MagenticBuilder API Tests
# =============================================================================


class TestMagenticBuilder:
    """Verify MagenticBuilder uses the new constructor-based API."""

    def test_magentic_builder_requires_participants(self):
        """MagenticBuilder requires participants as a constructor kwarg."""
        from agent_framework_orchestrations import MagenticBuilder
        with pytest.raises(TypeError, match="participants"):
            MagenticBuilder()  # Should fail without participants

    def test_magentic_builder_constructor_params(self):
        """MagenticBuilder constructor accepts all needed params."""
        from agent_framework_orchestrations import MagenticBuilder
        import inspect
        sig = inspect.signature(MagenticBuilder.__init__)
        params = set(sig.parameters.keys()) - {'self'}
        assert 'participants' in params
        assert 'manager_agent' in params
        assert 'max_round_count' in params
        assert 'max_stall_count' in params
        assert 'max_reset_count' in params
        assert 'progress_ledger_prompt' in params
        assert 'checkpoint_storage' in params
        assert 'enable_plan_review' in params

    def test_magentic_builder_has_build(self):
        """MagenticBuilder has build() method."""
        from agent_framework_orchestrations import MagenticBuilder
        assert hasattr(MagenticBuilder, 'build')

    def test_magentic_builder_no_old_methods(self):
        """MagenticBuilder no longer has the old chained builder methods."""
        from agent_framework_orchestrations import MagenticBuilder
        # Old API: .participants().with_manager().with_checkpointing()
        # The .participants() was a chained method, now it's a constructor param
        # with_manager() is gone, replaced by manager_agent constructor param
        assert not hasattr(MagenticBuilder, 'with_manager'), \
            "with_manager() replaced by constructor params"


# =============================================================================
# Section 7: Workflow.run() API Tests
# =============================================================================


class TestWorkflowRunAPI:
    """Verify Workflow.run() supports the new unified API."""

    def test_workflow_run_signature(self):
        """Workflow.run() accepts stream, responses, checkpoint_id, checkpoint_storage."""
        from agent_framework import Workflow
        import inspect
        sig = inspect.signature(Workflow.run)
        params = set(sig.parameters.keys()) - {'self'}
        assert 'stream' in params
        assert 'responses' in params
        assert 'checkpoint_id' in params
        assert 'checkpoint_storage' in params

    def test_workflow_no_old_streaming_methods(self):
        """Workflow no longer has run_stream/run_stream_from_checkpoint/send_responses_streaming."""
        from agent_framework import Workflow
        assert not hasattr(Workflow, 'run_stream'), "run_stream replaced by run(stream=True)"
        assert not hasattr(Workflow, 'run_stream_from_checkpoint'), \
            "run_stream_from_checkpoint replaced by run(checkpoint_id=..., stream=True)"
        assert not hasattr(Workflow, 'send_responses_streaming'), \
            "send_responses_streaming replaced by run(responses=..., stream=True)"


# =============================================================================
# Section 8: MCP Tool Tests
# =============================================================================


class TestMCPTools:
    """Verify MCPStreamableHTTPTool API compatibility."""

    def test_mcp_tool_constructor(self):
        """MCPStreamableHTTPTool accepts name, url, request_timeout + headers/timeout via kwargs."""
        from agent_framework import MCPStreamableHTTPTool
        import inspect
        sig = inspect.signature(MCPStreamableHTTPTool.__init__)
        params = set(sig.parameters.keys()) - {'self'}
        assert 'name' in params
        assert 'url' in params
        assert 'request_timeout' in params
        # headers and timeout are now accepted via **kwargs
        assert 'kwargs' in params, "MCPStreamableHTTPTool should accept **kwargs for headers/timeout"

    def test_mcp_tool_is_context_manager(self):
        """MCPStreamableHTTPTool supports async context manager protocol."""
        from agent_framework import MCPStreamableHTTPTool
        assert hasattr(MCPStreamableHTTPTool, '__aenter__')
        assert hasattr(MCPStreamableHTTPTool, '__aexit__')


# =============================================================================
# Section 9: Agent Module Integration Tests (mock-based)
# =============================================================================


class TestSingleAgentIntegration:
    """Test single_agent.Agent can be constructed and wired up correctly."""

    def test_single_agent_init(self):
        """Agent can be instantiated with state_store and session_id."""
        from agents.agent_framework.single_agent import Agent
        store = {}
        agent = Agent(state_store=store, session_id="test-session")
        assert agent.session_id == "test-session"
        assert agent._agent is None
        assert agent._session is None
        assert agent._initialized is False

    def test_single_agent_has_tool_tracking(self):
        """Agent has tool tracking methods from mixin."""
        from agents.agent_framework.single_agent import Agent
        agent = Agent(state_store={}, session_id="test")
        assert hasattr(agent, 'get_tool_calls')
        assert hasattr(agent, 'track_function_call_start')
        assert hasattr(agent, 'finalize_tool_tracking')

    def test_single_agent_websocket_manager(self):
        """set_websocket_manager injects the WS manager."""
        from agents.agent_framework.single_agent import Agent
        agent = Agent(state_store={}, session_id="test")
        mock_manager = MagicMock()
        agent.set_websocket_manager(mock_manager)
        assert agent._ws_manager is mock_manager


class TestHandoffAgentIntegration:
    """Test handoff agent construction and native HandoffBuilder integration.

    The handoff agent was rewritten in 1.2.x to use the native
    ``HandoffBuilder`` orchestration (no more hand-rolled intent classifier
    or regex-based handoff detection).
    """

    def test_handoff_agent_init(self):
        """Handoff agent initializes with empty domain agent map and no current domain."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import Agent
        store = {}
        agent = Agent(state_store=store, session_id="handoff-test")
        assert agent._current_domain is None
        assert agent._domain_agents == {}
        assert agent._workflow is None
        assert agent._initialized is False

    def test_handoff_agent_restores_domain(self):
        """Handoff agent restores current domain from state_store."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import Agent
        store = {"handoff-test_current_domain": "crm_billing"}
        agent = Agent(state_store=store, session_id="handoff-test")
        assert agent._current_domain == "crm_billing"

    def test_handoff_uses_native_handoff_builder(self):
        """The handoff agent module imports HandoffBuilder from agent_framework_orchestrations."""
        from agents.agent_framework.multi_agent import handoff_multi_domain_agent as mod
        from agent_framework_orchestrations import HandoffBuilder, HandoffAgentUserRequest
        # The rewritten module should reference the native HandoffBuilder API
        assert mod.HandoffBuilder is HandoffBuilder
        assert mod.HandoffAgentUserRequest is HandoffAgentUserRequest

    def test_handoff_no_legacy_classifier_attributes(self):
        """The 1.0.0rc1 hand-rolled classifier helpers were removed in 1.2.x."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import Agent
        agent = Agent(state_store={}, session_id="handoff-test")
        # These were the old hand-rolled helpers; native HandoffBuilder replaces them
        assert not hasattr(agent, "_detect_handoff_request"), (
            "Regex-based handoff detection was removed; HandoffBuilder injects "
            "synthetic handoff tools that are intercepted via middleware."
        )
        assert not hasattr(agent, "_classify_intent"), (
            "Hand-rolled intent classifier was removed; agents now decide "
            "handoffs themselves by calling the auto-generated handoff tools."
        )
        assert not hasattr(agent, "_domain_sessions"), (
            "Per-domain AgentSessions were removed; the workflow's checkpoint "
            "storage manages conversation state across handoffs."
        )

    def test_handoff_domains_have_descriptions(self):
        """Each domain config must have a description (used by HandoffBuilder for tool docs)."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import DOMAINS
        assert set(DOMAINS) == {"crm_billing", "product_promotions", "security_authentication"}
        for domain_id, cfg in DOMAINS.items():
            assert cfg.get("description"), (
                f"Domain '{domain_id}' must have a description; HandoffBuilder uses "
                f"it to generate the auto-injected handoff tool description."
            )


class TestReflectionAgentIntegration:
    """Test reflection agent construction."""

    def test_reflection_agent_init(self):
        """Reflection agent initializes with primary + reviewer agents."""
        from agents.agent_framework.multi_agent.reflection_agent import Agent
        agent = Agent(state_store={}, session_id="reflect-test")
        assert agent._primary_agent is None
        assert agent._reviewer is None
        assert agent._session is None
        assert agent._max_refinements == 2

    def test_reflection_approval_detection(self):
        """Reviewer approval detection works."""
        from agents.agent_framework.multi_agent.reflection_agent import Agent
        agent = Agent(state_store={}, session_id="test")
        assert agent._is_approved("APPROVE - looks good")
        assert not agent._is_approved("Needs improvement on point 3")

    def test_reflection_agent_uses_1_2_1_chat_client_kwargs(self):
        """The reflection agent must use 1.2.x kwarg names (model, azure_endpoint).

        The chat client is constructed via ``OpenAIChatClient(**client_kwargs)``,
        so the kwarg dict keys must match the new API names — this is a
        common foot-gun when migrating from 1.0.0rc1.
        """
        import inspect
        from agents.agent_framework.multi_agent import reflection_agent as mod
        src = inspect.getsource(getattr(mod.Agent, "_setup_agents"))
        # Old-API key strings should not appear in the setup code path
        assert '"deployment_name"' not in src, (
            "reflection_agent passes 'deployment_name' to OpenAIChatClient; "
            "rename to 'model' for the 1.2.x API."
        )
        # Note: a literal `'endpoint':` could also match the unrelated HTTP endpoint
        # field, so we look for the specific Azure key-rename pattern instead.
        assert '"endpoint": self.azure_openai_endpoint' not in src, (
            "reflection_agent passes 'endpoint' to OpenAIChatClient; "
            "rename to 'azure_endpoint' for the 1.2.x API."
        )


class TestMagenticGroupIntegration:
    """Test magentic group agent construction."""

    def test_magentic_agent_init(self):
        """Magentic agent initializes with configuration."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        agent = Agent(state_store={}, session_id="magentic-test")
        assert agent._max_round_count == 4
        assert agent._max_stall_count == 2

    def test_magentic_checkpoint_storage(self):
        """DictCheckpointStorage works for checkpointing."""
        from agents.agent_framework.multi_agent.magentic_group import DictCheckpointStorage
        from agent_framework import WorkflowCheckpoint
        
        backing = {}
        storage = DictCheckpointStorage(backing)
        assert storage.latest_checkpoint_id is None

    def test_magentic_checkpoint_storage_implements_1_2_1_protocol(self):
        """DictCheckpointStorage implements the 1.2.x CheckpointStorage protocol.

        In 1.0.0rc1 the methods were named save_checkpoint/load_checkpoint/...; in
        1.2.x they are save/load/delete/get_latest with workflow_name kwargs.
        """
        from agents.agent_framework.multi_agent.magentic_group import DictCheckpointStorage
        import inspect
        for name in ("save", "load", "delete", "get_latest", "list_checkpoints", "list_checkpoint_ids"):
            assert callable(getattr(DictCheckpointStorage, name, None)), (
                f"DictCheckpointStorage must implement 1.2.x method {name!r}"
            )
        # Old method names should NOT exist
        assert not hasattr(DictCheckpointStorage, "save_checkpoint"), \
            "save_checkpoint was renamed to save in 1.2.x"
        assert not hasattr(DictCheckpointStorage, "load_checkpoint"), \
            "load_checkpoint was renamed to load in 1.2.x"
        # workflow_name keyword-only enforcement
        for name in ("list_checkpoints", "list_checkpoint_ids", "get_latest"):
            sig = inspect.signature(getattr(DictCheckpointStorage, name))
            assert "workflow_name" in sig.parameters, (
                f"{name} must accept workflow_name keyword in 1.2.x"
            )

    def test_handoff_checkpoint_storage_implements_1_2_1_protocol(self):
        """The handoff agent's _DictCheckpointStorage matches the 1.2.x protocol."""
        from agents.agent_framework.multi_agent.handoff_multi_domain_agent import _DictCheckpointStorage
        for name in ("save", "load", "delete", "get_latest", "list_checkpoints", "list_checkpoint_ids"):
            assert callable(getattr(_DictCheckpointStorage, name, None)), (
                f"_DictCheckpointStorage must implement 1.2.x method {name!r}"
            )

    def test_workflow_checkpoint_uses_workflow_name(self):
        """WorkflowCheckpoint uses workflow_name (was workflow_id in 1.0.0rc1)."""
        from agent_framework import WorkflowCheckpoint
        import inspect
        sig = inspect.signature(WorkflowCheckpoint.__init__)
        assert "workflow_name" in sig.parameters
        assert "workflow_id" not in sig.parameters, \
            "workflow_id was renamed to workflow_name in 1.2.x"

    def test_dict_checkpoint_storage_save_load_roundtrip(self):
        """save() persists a checkpoint that load()/get_latest() can recover."""
        from agents.agent_framework.multi_agent.magentic_group import DictCheckpointStorage
        from agent_framework import WorkflowCheckpoint

        storage = DictCheckpointStorage({})
        cp = WorkflowCheckpoint(workflow_name="wf-A", graph_signature_hash="hash-1", checkpoint_id="cp-1")

        cid = asyncio.get_event_loop().run_until_complete(storage.save(cp))
        assert cid == "cp-1"

        loaded = asyncio.get_event_loop().run_until_complete(storage.load("cp-1"))
        assert loaded is not None
        assert loaded.workflow_name == "wf-A"
        assert loaded.checkpoint_id == "cp-1"

        latest = asyncio.get_event_loop().run_until_complete(storage.get_latest(workflow_name="wf-A"))
        assert latest is not None and latest.checkpoint_id == "cp-1"

        # get_latest with a non-matching workflow_name returns None
        none = asyncio.get_event_loop().run_until_complete(storage.get_latest(workflow_name="other"))
        assert none is None

    def test_get_latest_checkpoint_id_uses_workflow_name_kwarg(self):
        """_get_latest_checkpoint_id resumes from a 1.2.x-protocol-only storage.

        Storages that follow the 1.2.x ``CheckpointStorage`` protocol require
        the keyword-only ``workflow_name`` argument on ``get_latest`` /
        ``list_checkpoints`` / ``list_checkpoint_ids`` and do not expose the
        nonstandard ``latest_checkpoint_id`` convenience. The resume helper
        must call those methods with ``workflow_name=`` so it can still find
        the latest checkpoint.
        """
        from agents.agent_framework.multi_agent.magentic_group import Agent, DictCheckpointStorage
        from agent_framework import WorkflowCheckpoint

        # Back the storage with a dict that records the workflow_name so
        # _workflow_name_for_storage can recover it (mirrors how save() works).
        backing: dict = {"workflow_name": "wf-resume"}
        storage = DictCheckpointStorage(backing)
        cp = WorkflowCheckpoint(workflow_name="wf-resume", graph_signature_hash="h", checkpoint_id="cp-latest")
        asyncio.get_event_loop().run_until_complete(storage.save(cp))

        agent = Agent(state_store={}, session_id="test")
        latest_id = asyncio.get_event_loop().run_until_complete(agent._get_latest_checkpoint_id(storage))
        assert latest_id == "cp-latest"

    def test_magentic_sanitize_final_answer(self):
        """FINAL_ANSWER prefix is stripped from workflow output."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        agent = Agent(state_store={}, session_id="test")
        assert agent._sanitize_final_answer("FINAL_ANSWER: Hello world") == "Hello world"
        assert agent._sanitize_final_answer("Just a normal response") == "Just a normal response"
        assert agent._sanitize_final_answer(None) is None

    def test_magentic_extract_text_from_event(self):
        """Text extraction handles various WorkflowEvent data formats."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        from agent_framework import WorkflowEvent
        
        # Plain string data
        event = WorkflowEvent.output("exec1", "Hello")
        assert Agent._extract_text_from_event(event) == "Hello"
        
        # Object with .text attribute
        mock_msg = MagicMock()
        mock_msg.text = "From message"
        event2 = WorkflowEvent.output("exec1", mock_msg)
        assert Agent._extract_text_from_event(event2) == "From message"

    def test_magentic_process_output_event(self):
        """_process_workflow_event handles output events correctly."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        from agent_framework import WorkflowEvent
        
        agent = Agent(state_store={}, session_id="test")
        ws_manager = AsyncMock()
        agent.set_websocket_manager(ws_manager)
        
        event = WorkflowEvent.output("exec1", "Final answer text")
        asyncio.get_event_loop().run_until_complete(
            agent._process_workflow_event(event)
        )
        
        ws_manager.broadcast.assert_called()
        call_args = ws_manager.broadcast.call_args[0]
        assert call_args[0] == "test"  # session_id
        msg = call_args[1]
        assert msg["type"] == "final_result"

    def test_magentic_process_data_event(self):
        """_process_workflow_event handles streaming data events."""
        from agents.agent_framework.multi_agent.magentic_group import Agent
        from agent_framework import WorkflowEvent
        
        agent = Agent(state_store={}, session_id="test")
        ws_manager = AsyncMock()
        agent.set_websocket_manager(ws_manager)
        
        # Create a mock data event with text
        mock_data = MagicMock()
        mock_data.text = "streaming token"
        event = WorkflowEvent.emit("crm_billing", mock_data)
        
        asyncio.get_event_loop().run_until_complete(
            agent._process_workflow_event(event)
        )
        
        # Should broadcast agent_start and agent_token
        assert ws_manager.broadcast.call_count >= 1


# =============================================================================
# Section 10: Framework Version Check
# =============================================================================


class TestFrameworkVersion:
    """Verify we're running against the expected 1.2.x version."""

    def test_agent_framework_version(self):
        """agent_framework is at 1.2.1."""
        import agent_framework
        assert agent_framework.__version__ == "1.2.1", \
            f"Expected 1.2.1, got {agent_framework.__version__}"

    def test_agent_framework_core_installed(self):
        """agent-framework-core is installed at 1.2.1 as a dependency."""
        import importlib.metadata
        version = importlib.metadata.version('agent-framework-core')
        assert version == "1.2.1", \
            f"Expected 1.2.1, got {version}"
