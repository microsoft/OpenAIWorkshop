"""
Run evaluation on the agent configured in .env file.

This script:
1. Reads AGENT_MODULE from .env (same as backend.py does)
2. Loads that agent dynamically
3. Runs all test cases from eval_dataset.json
4. Captures traces and evaluates performance

Usage:
    cd agentic_ai/applications
    uv run python ../evaluations/run_agent_eval.py

Prerequisites:
    - MCP server must be running (cd mcp && uv run python mcp_service.py)
    - .env file must be configured in agentic_ai/applications/
"""

import os
import sys
import asyncio
import json
import warnings
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Suppress async generator cleanup warnings from MCP client
warnings.filterwarnings("ignore", message=".*async_generator.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*cancel scope.*")

# Add parent directory to Python path so we can import agents module
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Debug: Print the path that was added
print(f"🔍 Added to Python path: {parent_dir}")
print(f"🔍 Agents directory exists: {(parent_dir / 'agents').exists()}")

# Note: No telemetry setup needed - using HTTP requests to backend with telemetry

# Suppress asyncio error logs about async generator cleanup
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Add project paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "applications"))

# Load environment from applications/.env (or current directory .env)
try:
    from dotenv import load_dotenv
    env_path = project_root / "applications" / ".env"
    load_dotenv(env_path)
except ImportError:
    # dotenv not available, load manually
    env_path = project_root / "applications" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"')

print("=" * 80)
print("AI AGENT EVALUATION - Using Agent from .env")
print("=" * 80)

# Import evaluation framework
from evaluations import AgentEvaluationRunner, AgentTrace


class ToolCallTracker:
    """Captures tool calls emitted via the agent's WebSocket-style broadcast.

    This mirrors the lightweight tracker used in run_batch_eval.py: any
    broadcast message with type == "tool_called" is recorded so that the
    evaluator can score tool usage and completeness for Agent Framework
    agents (including the handoff multi-domain pattern).
    """

    def __init__(self) -> None:
        self.tool_calls: List[Dict[str, Any]] = []

    async def broadcast(self, session_id: str, message: dict) -> None:
        if isinstance(message, dict) and message.get("type") == "tool_called":
            tool_name = message.get("tool_name")
            if tool_name:
                # Evaluator only needs the tool name; args/results are optional
                self.tool_calls.append({"name": tool_name})


async def run_agent_on_query(agent_instance, query: str, session_id: str) -> tuple[str, List[Dict[str, Any]]]:
    """Run the agent on a single query and capture response + tool calls.

    For Agent Framework agents (single, handoff, reflection, etc.), we inject a
    ToolCallTracker via set_websocket_manager so that tool_called events emitted
    during MCP tool invocations are captured for evaluation.
    """
    captured_tools: List[Dict[str, Any]] = []

    # Inject tool-call tracker if the agent supports a WebSocket manager
    tracker: ToolCallTracker | None = None
    if hasattr(agent_instance, "set_websocket_manager"):
        tracker = ToolCallTracker()
        agent_instance.set_websocket_manager(tracker)

    try:
        # Run agent using the same methods as backend.py
        if hasattr(agent_instance, "chat_async"):
            # Agent Framework agents
            result = await agent_instance.chat_async(query)
            response_text = str(result) if result else "No response"

        elif hasattr(agent_instance, "chat_stream"):
            # Autogen streaming agents - collect full response
            response_parts = []
            async for event in agent_instance.chat_stream(query):
                if hasattr(event, 'content'):
                    response_parts.append(str(event.content))
            response_text = " ".join(response_parts) if response_parts else "No response"

        else:
            # Fallback: try calling agent directly
            result = await agent_instance(query)
            response_text = str(result) if result else "No response"

        # Prefer tools captured via tracker for Agent Framework agents
        if tracker is not None and tracker.tool_calls:
            captured_tools = tracker.tool_calls
        else:
            # Fallbacks for agents that expose tool calls directly
            if hasattr(agent_instance, 'get_tool_calls'):
                captured_tools = agent_instance.get_tool_calls()
            elif hasattr(agent_instance, '_tool_calls'):
                captured_tools = agent_instance._tool_calls  # type: ignore[attr-defined]
            elif hasattr(agent_instance, 'tool_calls'):
                captured_tools = agent_instance.tool_calls  # type: ignore[attr-defined]

    except Exception as e:
        print(f"  ⚠ Error running agent: {e}")
        response_text = f"Error: {str(e)}"
        captured_tools = []

    return response_text, captured_tools


def format_trace_as_agent_messages(trace: AgentTrace) -> tuple[list, list]:
    """Convert an AgentTrace to the agent message schema expected by Foundry evaluators.
    
    Returns:
        tuple: (query_messages, response_messages) in OpenAI-style agent message format
    """
    from datetime import datetime
    
    # Build query as list of messages (system + user query)
    query_messages = [
        {
            "role": "system",
            "content": "You are a helpful customer service agent for Contoso."
        },
        {
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": trace.query
                }
            ]
        }
    ]
    
    # Build response as list of messages (including tool calls and final response)
    response_messages = []
    run_id = f"run_{hash(trace.query) % 100000:05d}"
    
    # Add tool calls if any
    for i, tool_call in enumerate(trace.tool_calls):
        tool_name = tool_call.get("name", "unknown_tool")
        tool_args = tool_call.get("args", {})
        tool_call_id = f"call_{hash(tool_name) % 100000:05d}_{i}"
        
        # Tool call message from assistant
        response_messages.append({
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "run_id": run_id,
            "role": "assistant",
            "content": [
                {
                    "type": "tool_call",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "arguments": tool_args if isinstance(tool_args, dict) else {}
                }
            ]
        })
        
        # Tool result message
        response_messages.append({
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "run_id": run_id,
            "tool_call_id": tool_call_id,
            "role": "tool",
            "content": [
                {
                    "type": "tool_result",
                    "tool_result": tool_call.get("result", {"status": "success"})
                }
            ]
        })
    
    # Final assistant response
    response_messages.append({
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": trace.response
            }
        ]
    })
    
    return query_messages, response_messages


async def run_foundry_evaluation(traces: List[AgentTrace], data_file: Path, agent_name: str, test_cases: List[Dict[str, Any]] = None, eval_type: str = "mixed"):
    """Run evaluation using Azure AI Projects SDK and log results to Foundry portal.
    
    Uses the openai_client.evals API (azure-ai-projects>=2.0.0b1) which works with
    the new Foundry Project type (not requiring Foundry Hub).
    
    Args:
        traces: List of agent traces with query/response pairs
        data_file: Path to the JSONL data file
        agent_name: Name of the agent for labeling
        test_cases: Optional list of test cases with ground_truth for solution_accuracy
        eval_type: Type of evaluation - "single-turn", "multi-turn", or "mixed"
    """
    import time
    
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as e:
        print(f"❌ Azure AI Projects SDK not installed: {e}")
        print("   Install with: uv add 'azure-ai-projects>=2.0.0b1' azure-identity")
        return
    
    # Get project endpoint from environment
    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    
    if not project_endpoint:
        print("❌ Missing AZURE_AI_PROJECT_ENDPOINT in .env file")
        print("   Get this from: Azure AI Foundry → Your Project → Home page")
        print("   Example: https://eastus2.api.azureml.ms/api/projects/your-project-name")
        return
    
    print(f"📤 Azure AI Project Endpoint: {project_endpoint}")
    print(f"🏷️ Agent name: {agent_name}")
    print(f"📊 Traces to evaluate: {len(traces)}")
    
    try:
        # Connect to AI Project
        credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=credential,
        )
        
        with project_client:
            # Get the OpenAI-compatible client from the project.
            #
            # azure-ai-projects >= 2.1.0 routes get_openai_client() at the new
            # unified "/v1" path, which REJECTS the legacy "api-version" query
            # parameter ("api-version query parameter is not allowed when using
            # /v1 path"). Older pre-release SDKs needed api-version forced. So we
            # try the modern (no api-version) call first and only fall back to
            # forcing api-version if the installed SDK requires it.
            try:
                openai_client = project_client.get_openai_client()
            except TypeError:
                # Very old SDKs require an explicit api_version kwarg.
                openai_client = project_client.get_openai_client(
                    api_version="2025-11-15-preview"
                )
            
            # Diagnostic logging for CI debugging
            import azure.ai.projects
            print(f"📋 SDK versions: azure-ai-projects={azure.ai.projects.__version__}, openai={__import__('openai').__version__}")
            print(f"📋 OpenAI base_url: {openai_client.base_url}")
            if hasattr(openai_client, '_custom_query'):
                print(f"📋 API version: {openai_client._custom_query}")
            
            # Check if the project has evals capability
            if not hasattr(openai_client, 'evals'):
                print("⚠️ This project doesn't support the evals API.")
                print("   Make sure you have azure-ai-projects>=2.0.0b1 installed")
                return
            
            # Define the evaluation schema for Azure AI built-in evaluators
            # Note: tool_calls and tool_definitions removed due to Foundry API schema issues
            data_source_config = {
                "type": "custom",
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "response": {"type": "string"},
                        "context": {"type": "string"},
                        "ground_truth": {"type": "string"}
                    },
                    "required": ["query", "response"]
                },
                "include_sample_schema": True
            }
            
            # Get the model deployment name for LLM-based evaluators
            # First check for dedicated eval model, then fall back to chat deployment
            model_deployment_name = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
            print(f"📋 Evaluation model: {model_deployment_name}")
            
            # Check if using a reasoning model (GPT-5 or higher, o1, o3 models)
            # Reasoning models require different configuration (e.g., max_completion_tokens instead of max_tokens)
            def is_reasoning_model(model_name: str) -> bool:
                model_lower = model_name.lower()
                # Check for o-series reasoning models
                if model_lower.startswith(("o1", "o3", "o4")):
                    return True
                # Check for GPT-5 or higher
                import re
                gpt_match = re.search(r'gpt-?(\d+)', model_lower)
                if gpt_match:
                    version = int(gpt_match.group(1))
                    return version >= 5
                return False
            
            use_reasoning_model = is_reasoning_model(model_deployment_name)
            
            # Build initialization parameters - include is_reasoning_model for GPT-5+ and o-series models
            def get_init_params() -> dict:
                params = {"deployment_name": model_deployment_name}
                if use_reasoning_model:
                    params["is_reasoning_model"] = True
                return params
            
            # Define testing criteria using Azure AI built-in evaluators
            # These provide numeric scores (1-5 scale) with pass/fail labels and reasoning
            # See: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/agent-evaluate-sdk
            testing_criteria = [
                # Quality evaluators (5-point scale: 1=poor, 5=excellent)
                # Score >= 3 is considered passing by default
                {
                    "type": "azure_ai_evaluator",
                    "name": "coherence",
                    "evaluator_name": "builtin.coherence",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"}
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "fluency",
                    "evaluator_name": "builtin.fluency",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"}
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "relevance",
                    "evaluator_name": "builtin.relevance",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"}
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "groundedness",
                    "evaluator_name": "builtin.groundedness",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}",
                        "context": "{{item.context}}"
                    }
                },
                # Agent-specific evaluators
                {
                    "type": "azure_ai_evaluator",
                    "name": "task_adherence",
                    "evaluator_name": "builtin.task_adherence",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"}
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "intent_resolution",
                    "evaluator_name": "builtin.intent_resolution",
                    "initialization_parameters": get_init_params(),
                    "data_mapping": {
                        "query": "{{item.query}}",
                        "response": "{{item.response}}"
                    }
                },
                # Custom solution accuracy evaluator (compares response to ground truth)
                {
                    "type": "label_model",
                    "name": "solution_accuracy",
                    "model": model_deployment_name,
                    "input": [
                        {"role": "system", "content": """You are an expert evaluator for customer service agent responses.
Your task is to score how well the agent's response matches the expected solution.

Scoring Rubric (1-5):
5 - Excellent: Response fully addresses all aspects of the expected solution with accurate details
4 - Good: Response addresses most aspects correctly with minor omissions
3 - Adequate: Response addresses the main points but misses some details or has minor inaccuracies
2 - Poor: Response partially addresses the query but misses key information or has significant issues
1 - Very Poor: Response fails to address the query or contains major errors

Return ONLY a JSON object with:
- "choice": your score as a string ("1", "2", "3", "4", or "5")
- "reason": brief explanation of your score"""},
                        {"role": "user", "content": """Customer Query: {{item.query}}

Agent Response: {{item.response}}

Expected Solution (Ground Truth): {{item.ground_truth}}

Evaluate how well the agent's response matches the expected solution. Consider:
- Did the agent provide the correct information?
- Did the agent address all aspects of the customer's question?
- Is the response accurate based on the ground truth?"""}
                    ],
                    "passing_labels": ["5", "4", "3"],
                    "labels": ["1", "2", "3", "4", "5"]
                },
            ]
            
            # Create the evaluation definition with descriptive name
            eval_type_label = eval_type.replace("-", " ").title()  # "single-turn" -> "Single Turn"
            print(f"\n🚀 Creating evaluation in Foundry...")
            eval_obj = openai_client.evals.create(
                name=f"{agent_name} - {eval_type_label}",
                data_source_config=data_source_config,
                testing_criteria=testing_criteria
            )
            print(f"✓ Evaluation created (id: {eval_obj.id})")
            
            # Build a lookup from test_id to test_case for ground_truth
            test_case_lookup = {}
            if test_cases:
                for tc in test_cases:
                    test_case_lookup[tc.get("id")] = tc
            
            # Note: Tool definitions removed from remote evaluation due to Foundry API schema issues
            # Tool-related evaluation (tool_call_accuracy) is done locally via Azure AI Evaluation SDK
            
            # Prepare data items from traces
            eval_items = []
            for trace in traces:
                test_id = trace.metadata.get("test_id") if trace.metadata else None
                test_case = test_case_lookup.get(test_id, {}) if test_id else {}
                ground_truth = test_case.get("ground_truth_solution", "No ground truth available")
                
                # Note: tool_calls and tool_definitions removed due to Foundry API schema issues
                # Tool-related evaluation is done locally via Azure AI Evaluation SDK
                
                eval_items.append({
                    "item": {
                        "query": trace.query,
                        "response": trace.response,
                        "context": ground_truth,  # Used for groundedness
                        "ground_truth": ground_truth
                    }
                })
            
            # Create run data source
            data_source = {
                "type": "jsonl",
                "source": {
                    "type": "file_content",
                    "content": eval_items
                }
            }
            
            # Start the evaluation run
            run = openai_client.evals.runs.create(
                eval_id=eval_obj.id,
                name=f"{agent_name} | {eval_type_label} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                data_source=data_source
            )
            print(f"✓ Evaluation run started (id: {run.id})")
            
            # Wait for completion
            print("\n⏳ Waiting for evaluation to complete...")
            while run.status not in ["completed", "failed", "cancelled"]:
                time.sleep(3)
                run = openai_client.evals.runs.retrieve(
                    eval_id=eval_obj.id,
                    run_id=run.id
                )
                print(f"   Status: {run.status}")
            
            # Display results
            if run.status == "completed":
                print("\n✅ Evaluation run completed successfully!")
                
                if hasattr(run, 'result_counts') and run.result_counts:
                    rc = run.result_counts
                    total = rc.total if hasattr(rc, 'total') else 0
                    passed = rc.passed if hasattr(rc, 'passed') else 0
                    failed = rc.failed if hasattr(rc, 'failed') else 0
                    
                    print(f"\n📊 Results:")
                    print(f"   Total:  {total}")
                    print(f"   Passed: {passed} ✓")
                    print(f"   Failed: {failed} ✗")
                    if total > 0:
                        print(f"   Pass Rate: {passed/total:.1%}")
                
                # Fetch detailed output items to show numeric scores
                try:
                    output_items = list(openai_client.evals.runs.output_items.list(
                        eval_id=eval_obj.id,
                        run_id=run.id
                    ))
                    
                    if output_items:
                        print(f"\n📈 Detailed Scores by Evaluator (1-5 scale, threshold: 3):")
                        print("-" * 70)
                        
                        # Aggregate scores by evaluator
                        evaluator_scores: Dict[str, List[float]] = {}
                        evaluator_details: Dict[str, List[Dict]] = {}
                        
                        for item in output_items:
                            if hasattr(item, 'results') and item.results:
                                for result in item.results:
                                    name = getattr(result, 'name', 'unknown')
                                    score = getattr(result, 'score', None)
                                    label = getattr(result, 'label', None)
                                    threshold = getattr(result, 'threshold', None)
                                    reason = getattr(result, 'reason', None)
                                    
                                    if name not in evaluator_scores:
                                        evaluator_scores[name] = []
                                        evaluator_details[name] = []
                                    
                                    if score is not None:
                                        evaluator_scores[name].append(score)
                                        evaluator_details[name].append({
                                            'score': score,
                                            'label': label,
                                            'threshold': threshold,
                                            'reason': reason[:100] + '...' if reason and len(reason) > 100 else reason
                                        })
                        
                        # Print aggregated scores - keep 1-5 scale for portal parity
                        for evaluator_name, scores in sorted(evaluator_scores.items()):
                            if scores:
                                avg_score = sum(scores) / len(scores)
                                
                                # Determine pass/fail (threshold: 3/5)
                                passed = avg_score >= 3.0
                                status = "✓" if passed else "✗"
                                
                                # Create visual bar (scaled for 1-5 range)
                                bar_length = int(avg_score * 4)  # Max 20 chars at score 5
                                bar = "█" * bar_length
                                
                                print(f"   {evaluator_name:25} {avg_score:4.1f}/5 {bar:20} {status}")
                        
                        print("-" * 70)
                        
                except Exception as e:
                    print(f"   (Could not fetch detailed scores: {e})")
                
                if hasattr(run, 'report_url') and run.report_url:
                    print(f"\n🔗 View in Foundry portal:")
                    print(f"   {run.report_url}")
                else:
                    print(f"\n🔗 View results in Azure AI Foundry portal:")
                    print(f"   https://ai.azure.com")
                    
            else:
                print(f"\n❌ Evaluation run failed: {run.status}")
                if hasattr(run, 'error'):
                    print(f"   Error: {run.error}")
                    
    except Exception as e:
        print(f"❌ Error running Foundry evaluation: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Troubleshooting tips:")
        print("   1. Verify AZURE_AI_PROJECT_ENDPOINT is correct")
        print("   2. Make sure you're signed in: az login")
        print("   3. Check azure-ai-projects version: uv pip show azure-ai-projects")


async def main():
    """Main evaluation entry point."""
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run agent evaluations")
    parser.add_argument("--agent", default=None, 
                        help="Agent type: single, reflection, handoff (overrides --agent-name)")
    parser.add_argument("--agent-name", default="agent_eval", help="Name for telemetry tracking")
    parser.add_argument("--backend-url", default="http://localhost:7000", help="Backend URL to send requests to")
    parser.add_argument("--remote", action="store_true", help="Run evaluation in Azure AI Foundry portal only (skip local)")
    parser.add_argument("--local", action="store_true", help="Run local evaluation only (default if neither specified)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of test cases to run (0 = all)")
    parser.add_argument("--multi-turn-only", action="store_true", help="Only run multi-turn test cases")
    parser.add_argument("--single-turn-only", action="store_true", help="Only run single-turn test cases")
    parser.add_argument("--ci", action="store_true", help="CI mode: skip interactive prompts, auto-continue on MCP unavailability")
    args = parser.parse_args()
    
    # Determine agent name based on --agent flag
    if args.agent:
        agent_name = f"agent_{args.agent}"
    else:
        agent_name = args.agent_name
    
    backend_url = args.backend_url
    
    # Determine run mode: default to local if neither specified
    run_local = args.local or not args.remote
    run_remote = args.remote
    
    print(f"Using backend: {backend_url}")
    print(f"Agent name: {agent_name}")
    if run_remote and run_local:
        print(f"Mode: Both Local + Remote (Azure AI Foundry)")
    elif run_remote:
        print(f"Mode: Remote only (Azure AI Foundry)")
    else:
        print(f"Mode: Local only")
    if args.multi_turn_only:
        print(f"Filter: Multi-turn only")
    elif args.single_turn_only:
        print(f"Filter: Single-turn only")
    
    # 1. No need to load agent module - we're sending HTTP requests
    print(f"\n🌐 Using HTTP requests to backend instead of direct agent creation")
    
    # 2. Test backend connection
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            health_response = await client.get(f"{backend_url}/auth/config", timeout=5.0)
            print(f"✓ Backend is responding")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print(f"   Make sure backend is running on {backend_url}")
        return
    
    # 3. Check MCP server (skip in CI — backend connects to deployed MCP internally)
    if not args.ci:
        mcp_uri = os.getenv("MCP_SERVER_URI", "http://localhost:8000/mcp")
        print(f"\n🔌 MCP Server: {mcp_uri}")
        
        try:
            import requests
            health_check = requests.get(mcp_uri.replace("/mcp", "/health"), timeout=2)
            print(f"✓ MCP server is responding")
        except:
            print(f"⚠ WARNING: Could not connect to MCP server")
            print(f"   Make sure it's running: cd mcp && uv run python mcp_service.py")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                return
    
    # 4. Load test cases
    dataset_path = Path(__file__).parent / "eval_dataset.json"
    with open(dataset_path, encoding='utf-8') as f:
        data = json.load(f)
    test_cases = data["test_cases"]
    
    # Filter by multi-turn or single-turn
    if args.multi_turn_only:
        test_cases = [tc for tc in test_cases if tc.get("multi_turn", False)]
        print(f"\n🔄 Filtering to multi-turn test cases only")
    elif args.single_turn_only:
        test_cases = [tc for tc in test_cases if not tc.get("multi_turn", False)]
        print(f"\n📝 Filtering to single-turn test cases only")
    
    # Apply limit if specified
    if args.limit > 0:
        test_cases = test_cases[:args.limit]
        print(f"\n⚡ Limited to {args.limit} test case(s) for quick testing")
    
    # Count multi-turn scenarios
    multi_turn_count = sum(1 for tc in test_cases if tc.get("multi_turn", False))
    single_turn_count = len(test_cases) - multi_turn_count
    
    print(f"\n📋 Running {len(test_cases)} test cases")
    print(f"   - Single-turn: {single_turn_count}")
    print(f"   - Multi-turn: {multi_turn_count}")
    
    # 5. Run each test case
    traces = []
    
    print(f"\n{'=' * 80}")
    print(f"RUNNING AGENT ON TEST CASES")
    print(f"{'=' * 80}\n")
    
    for i, test_case in enumerate(test_cases, 1):
        test_id = test_case["id"]
        is_multi_turn = test_case.get("multi_turn", False)
        customer_id = test_case.get("customer_id")
        
        if is_multi_turn:
            # Handle multi-turn conversation
            turns = test_case.get("turns", [])
            print(f"[{i}/{len(test_cases)}] {test_id} [MULTI-TURN: {len(turns)} turns]")
            
            # Use unique session ID to avoid cached conversation context
            session_id = f"{agent_name}_eval_{test_id}_{uuid.uuid4().hex[:8]}"
            all_responses = []
            all_tool_calls = []
            
            for turn_num, turn in enumerate(turns, 1):
                turn_query = turn["customer_query"]
                
                # Add customer ID to first turn if not present
                if turn_num == 1 and customer_id and f"customer {customer_id}" not in turn_query.lower():
                    turn_query = f"I'm customer {customer_id}. {turn_query}"
                
                print(f"  Turn {turn_num}: {turn_query[:60]}...")
                
                try:
                    import httpx
                    
                    async with httpx.AsyncClient() as client:
                        response_obj = await client.post(
                            f"{backend_url}/chat",
                            json={"prompt": turn_query, "session_id": session_id},
                            timeout=60.0
                        )
                        response_obj.raise_for_status()
                        
                        result = response_obj.json()
                        response = result.get("response", "")
                        tools_used = result.get("tools_used", [])
                        
                        all_responses.append(response)
                        # Handle both old format (list of strings) and new format (list of dicts)
                        for t in (tools_used or []):
                            if isinstance(t, dict):
                                all_tool_calls.append(t)
                            else:
                                all_tool_calls.append({"name": t, "args": {}})
                        
                        print(f"    → Response: {response[:60]}... | Tools: {len(tools_used or [])}")
                        
                except Exception as e:
                    print(f"    ❌ Error in turn {turn_num}: {e}")
                    all_responses.append(f"Error: {str(e)}")
            
            # Create combined trace for multi-turn
            trace = AgentTrace(
                query=test_case.get("customer_query", turns[0]["customer_query"] if turns else ""),
                response="\n\n---\n\n".join(all_responses),
                tool_calls=all_tool_calls,
                metadata={
                    "test_id": test_id,
                    "agent_backend": backend_url,
                    "session_id": session_id,
                    "is_multi_turn": True,
                    "turn_count": len(turns),
                    "turn_responses": all_responses,
                }
            )
            traces.append(trace)
            
        else:
            # Handle single-turn conversation (original logic)
            query = test_case["customer_query"]
            
            # Augment query with customer ID if available
            if customer_id and f"customer {customer_id}" not in query.lower():
                query = f"I'm customer {customer_id}. {query}"
            
            print(f"[{i}/{len(test_cases)}] {test_id}")
            print(f"Query: {query[:80]}...")
            
            # Use unique session ID to avoid cached conversation context
            session_id = f"{agent_name}_eval_{test_id}_{uuid.uuid4().hex[:8]}"
            
            try:
                import httpx
                
                request_data = {
                    "prompt": query,
                    "session_id": session_id
                }
                
                async with httpx.AsyncClient() as client:
                    response_obj = await client.post(
                        f"{backend_url}/chat",
                        json=request_data,
                        timeout=60.0
                    )
                    response_obj.raise_for_status()
                    
                    result = response_obj.json()
                    response = result.get("response", "")
                    tools_used = result.get("tools_used", [])
                    
                    # Handle both old format (list of strings) and new format (list of dicts)
                    tool_calls = []
                    for t in (tools_used or []):
                        if isinstance(t, dict):
                            tool_calls.append(t)
                        else:
                            tool_calls.append({"name": t, "args": {}})
                
                print(f"  ✓ Response: {response[:100]}...")
                print(f"  ✓ Tools called: {len(tool_calls)}")
                
                trace = AgentTrace(
                    query=test_case["customer_query"],
                    response=response,
                    tool_calls=tool_calls,
                    metadata={
                        "test_id": test_id,
                        "agent_backend": backend_url,
                        "session_id": session_id,
                        "augmented_query": query,
                        "is_multi_turn": False,
                    }
                )
                traces.append(trace)
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                trace = AgentTrace(
                    query=query,
                    response=f"Error: {str(e)}",
                    tool_calls=[],
                    metadata={
                        "test_id": test_id,
                        "agent_backend": backend_url,
                        "error": str(e),
                        "is_multi_turn": False,
                    }
                )
                traces.append(trace)
        
        print()
    
    # 6. Generate evaluation_input_data.jsonl for Foundry integration
    print(f"{'=' * 80}")
    print(f"GENERATING FOUNDRY DATA FILE")
    print(f"{'=' * 80}\n")
    
    foundry_data_file = Path(__file__).parent / "evaluation_input_data.jsonl"
    with open(foundry_data_file, 'w') as f:
        for trace in traces:
            # Extract test case data from metadata
            test_id = trace.metadata.get("test_id", "unknown")
            
            # Find matching test case from original dataset
            matching_test = None
            for test_case in test_cases:
                if test_case.get("id") == test_id:
                    matching_test = test_case
                    break
            
            # Prepare data in format expected by run_eval.py
            foundry_row = {
                "query": trace.query,
                "response": trace.response,
                "expected_tools": matching_test.get("expected_tools", []) if matching_test else [],
                "required_tools": matching_test.get("required_tools", []) if matching_test else [],
                "success_criteria": matching_test.get("success_criteria", {}) if matching_test else {},
                "tool_calls": [{"name": tc["name"], "args": tc.get("args", {})} for tc in trace.tool_calls]
            }
            
            f.write(json.dumps(foundry_row) + '\n')
    
    print(f"✓ Generated {foundry_data_file} with {len(traces)} evaluation rows")
    
    # 7. Run local evaluation (if --local or neither flag specified)
    if run_local:
        print(f"{'=' * 80}")
        print(f"EVALUATING RESULTS (LOCAL)")
        print(f"{'=' * 80}\n")
        
        runner = AgentEvaluationRunner(dataset_path=str(dataset_path))
        summary = runner.run_evaluation(
            traces,
            output_dir=str(Path(__file__).parent / "eval_results")
        )
        
        # Display summary
        print(f"\n{'=' * 80}")
        print(f"EVALUATION SUMMARY - {backend_url}")
        print(f"{'=' * 80}")
        print(f"Agent: {agent_name}")
        print(f"Total Tests:    {summary['total_tests']}")
        print(f"Passed:         {summary['passed']} ✓")
        print(f"Failed:         {summary['failed']} ✗")
        print(f"Pass Rate:      {summary['pass_rate']:.1%}")
        print(f"Average Score:  {summary['average_score']:.2f}")
        
        # Show different metric emphasis for multi-turn vs single-turn
        if args.multi_turn_only:
            print(f"\n📊 Multi-Turn Metrics (outcome-focused, 1-5 scale, threshold: 3):")
            outcome_metrics = ["solution_accuracy", "task_adherence", "intent_resolution", "coherence", "fluency", "relevance"]
            for metric in outcome_metrics:
                score = summary['metric_averages'].get(metric, 0)
                bar = "█" * int(score * 4)
                status = "✓" if score >= 3.0 else "✗"
                print(f"  {metric:30s}: {score:4.1f}/5 {bar:20} {status}")
        else:
            print(f"\nMetric Breakdown (1-5 scale, threshold: 3):")
            for metric, score in summary['metric_averages'].items():
                bar = "█" * int(score * 4)  # Scale bar for 1-5 range (max 20 chars at score 5)
                status = "✓" if score >= 3.0 else "✗"
                print(f"  {metric:30s}: {score:4.1f}/5 {bar:20} {status}")
        
        print(f"\n{'=' * 80}")
        print(f"✓ Local evaluation complete! Check eval_results/ for detailed reports.")
        print(f"{'=' * 80}\n")
    
    # 8. Push to Azure AI Foundry if --remote flag is set
    if run_remote:
        print(f"{'=' * 80}")
        print(f"PUSHING RESULTS TO AZURE AI FOUNDRY")
        print(f"{'=' * 80}\n")
        
        # Check for required environment variable
        project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        
        if not project_endpoint:
            print("❌ Missing AZURE_AI_PROJECT_ENDPOINT in .env file")
            print("   Get this from: Azure AI Foundry → Your Project → Settings → Project details")
            print("   Example: https://your-account.services.ai.azure.com/api/projects/your-project")
            print("\n   Skipping remote evaluation...")
        else:
            # Determine eval type for naming
            if args.multi_turn_only:
                eval_type = "multi-turn"
            elif args.single_turn_only:
                eval_type = "single-turn"
            else:
                eval_type = "mixed"
            
            # Use the new Azure AI Projects SDK approach (azure-ai-projects>=2.0.0b1)
            # This uses openai_client.evals API instead of azure.ai.evaluation.evaluate()
            await run_foundry_evaluation(traces, foundry_data_file, agent_name, test_cases, eval_type)
    
    # Give async tasks time to cleanup
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nEvaluation cancelled by user.")
    finally:
        # Ensure all async resources are cleaned up
        pass
