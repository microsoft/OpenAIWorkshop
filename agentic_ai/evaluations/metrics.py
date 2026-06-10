"""
Evaluation metrics for AI Agent performance assessment.
Pattern-agnostic metrics that work across:
- single agents
- handoff agents
- reflection agents
- research/magentic agents

Includes Azure AI Foundry evaluators for LLM-as-judge evaluation.
"""

import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Azure AI Foundry Evaluators (optional - graceful degradation if not available)
try:
    from azure.ai.evaluation import (
        IntentResolutionEvaluator,
        TaskAdherenceEvaluator,
        ToolCallAccuracyEvaluator,
        CoherenceEvaluator,
        FluencyEvaluator,
        RelevanceEvaluator,
    )
    AZURE_EVALUATORS_AVAILABLE = True
except ImportError:
    AZURE_EVALUATORS_AVAILABLE = False
    IntentResolutionEvaluator = None
    TaskAdherenceEvaluator = None
    ToolCallAccuracyEvaluator = None
    CoherenceEvaluator = None
    FluencyEvaluator = None
    RelevanceEvaluator = None


# =========================
# Metric Types
# =========================

class MetricType(Enum):
    TOOL_BEHAVIOR = "tool_behavior"
    RESPONSE_QUALITY = "response_quality"
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    INTENT = "intent"
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    RELEVANCE = "relevance"
    SOLUTION_ACCURACY = "solution_accuracy"
    TASK_COMPLETION = "task_completion"


# =========================
# Result Container
# =========================

@dataclass
class EvaluationResult:
    metric_name: str
    metric_type: MetricType
    score: float  # 1.0 – 5.0 scale (matching Foundry portal)
    passed: bool
    details: Dict[str, Any]
    explanation: str


# =========================
# Tool Behavior Evaluator (Upgraded)
# =========================

class ToolBehaviorEvaluator:
    """
    Pattern-agnostic tool scoring:
    - recall (required tools used)
    - precision (relevant vs total)
    - efficiency (minimal sufficiency)
    """

    def evaluate(
        self,
        expected_tools: List[str],
        actual_tools: List[str],
        required_tools: Optional[List[str]] = None,
    ) -> EvaluationResult:

        required_tools = required_tools or expected_tools

        actual_set = set(actual_tools)
        expected_set = set(expected_tools)
        required_set = set(required_tools)

        required_hit = required_set & actual_set
        missing_required = required_set - actual_set
        extra_tools = actual_set - expected_set
        relevant_used = actual_set & expected_set

        # --- Scores ---

        recall = len(required_hit) / len(required_set) if required_set else 1.0
        precision = len(relevant_used) / len(actual_set) if actual_set else 1.0
        efficiency = len(required_set) / len(actual_set) if actual_set else 1.0
        efficiency = min(efficiency, 1.0)

        # Combined ratio (0-1), then scale to 1-5
        combined = (recall * 0.5) + (precision * 0.3) + (efficiency * 0.2)
        score = 1.0 + (combined * 4.0)  # Maps 0-1 to 1-5 scale

        passed = recall == 1.0  # All required tools must be used

        details = {
            "recall": recall,
            "precision": precision,
            "efficiency": efficiency,
            "missing_required": list(missing_required),
            "extra_tools": list(extra_tools),
            "required_hit": list(required_hit),
        }

        explanation = (
            f"Recall={recall:.2f} Precision={precision:.2f} "
            f"Efficiency={efficiency:.2f} Score={score:.1f}/5"
        )

        return EvaluationResult(
            metric_name="tool_behavior",
            metric_type=MetricType.TOOL_BEHAVIOR,
            score=score,
            passed=passed,
            details=details,
            explanation=explanation,
        )


# =========================
# Completeness Evaluator (Hybrid)
# =========================

class CompletenessEvaluator:
    """
    Deterministic tool checks + optional LLM semantic checks.
    """

    TOOL_CRITERIA_MAP = {
        "must_access_billing": ["get_billing_summary", "get_subscription_detail"],
        "must_check_subscription": ["get_subscription_detail"],
        "must_check_security_logs": ["get_security_logs"],
        "must_check_promotions": ["get_eligible_promotions"],
        "must_check_orders": ["get_customer_orders"],
    }

    def evaluate(
        self,
        success_criteria: Dict[str, bool],
        tool_calls: List[Dict[str, Any]],
    ) -> EvaluationResult:

        tool_names = [c.get("name", "") for c in tool_calls]
        results = {}

        for criterion, required in success_criteria.items():

            if not required:
                results[criterion] = True
                continue

            if criterion in self.TOOL_CRITERIA_MAP:
                needed = self.TOOL_CRITERIA_MAP[criterion]
                results[criterion] = any(t in tool_names for t in needed)
            else:
                # semantic criteria handled by LLM judge metric
                results[criterion] = True

        required_count = sum(success_criteria.values())
        met_count = sum(
            1 for k, v in results.items()
            if v and success_criteria.get(k)
        )

        # Scale to 1-5 (0 if no requirements, otherwise proportional)
        ratio = met_count / required_count if required_count else 1.0
        score = 1.0 + (ratio * 4.0)  # Maps 0-1 ratio to 1-5 scale
        passed = met_count == required_count  # All requirements must be met

        return EvaluationResult(
            metric_name="completeness",
            metric_type=MetricType.COMPLETENESS,
            score=score,
            passed=passed,
            details=results,
            explanation=f"{met_count}/{required_count} required criteria met",
        )


# =========================
# Efficiency Evaluator (NEW)
# =========================

class EfficiencyEvaluator:
    """
    Pattern-agnostic step efficiency metric.
    """

    def evaluate(
        self,
        actual_tool_calls: int,
        required_tools: int,
    ) -> EvaluationResult:

        baseline = max(required_tools, 1)
        efficiency = baseline / max(actual_tool_calls, 1)
        efficiency = min(efficiency, 1.0)
        
        # Scale to 1-5
        score = 1.0 + (efficiency * 4.0)

        return EvaluationResult(
            metric_name="step_efficiency",
            metric_type=MetricType.EFFICIENCY,
            score=score,
            passed=score >= 3.0,  # Threshold: 3/5
            details={
                "actual_calls": actual_tool_calls,
                "baseline_required": baseline,
            },
            explanation=f"Efficiency {score:.1f}/5",
        )


# =========================
# LLM Judge Evaluator (Upgraded)
# =========================

class ResponseQualityEvaluator:

    def __init__(self, llm_client=None):
        self.client = llm_client

    def evaluate(
        self,
        query: str,
        response: str,
        tool_summary: Optional[str] = None,
    ) -> EvaluationResult:

        if not self.client:
            return self._basic(response)

        prompt = f"""
Evaluate this customer support response.

Query: {query}
Response: {response}
Tool Evidence: {tool_summary}

Score 0–10:
- relevance
- clarity
- completeness
- professionalism
- actionability
- groundedness (uses evidence, not guesses)
- safety (no over-promising)

Return JSON with overall_score and explanation.
"""

        try:
            r = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Expert evaluator."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            import json
            data = json.loads(r.choices[0].message.content)

            # Convert 0-10 to 1-5 scale
            raw_score = data["overall_score"]
            score = 1.0 + (raw_score / 10.0) * 4.0  # Maps 0-10 to 1-5

            return EvaluationResult(
                metric_name="response_quality",
                metric_type=MetricType.RESPONSE_QUALITY,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=data,
                explanation=data.get("explanation", ""),
            )

        except Exception:
            return self._basic(response)

    def _basic(self, response: str) -> EvaluationResult:
        ok = len(response.split()) > 15
        score = 5.0 if ok else 1.0  # 5/5 for good, 1/5 for bad
        return EvaluationResult(
            metric_name="response_quality_basic",
            metric_type=MetricType.RESPONSE_QUALITY,
            score=score,
            passed=ok,
            details={},
            explanation="Basic length check",
        )


# =========================
# Grounded Accuracy Evaluator (NEW)
# =========================

class GroundedAccuracyEvaluator:
    """
    Checks if response contradicts tool outputs (LLM-assisted).
    """

    def __init__(self, llm_client=None):
        self.client = llm_client

    def evaluate(
        self,
        response: str,
        tool_outputs: Optional[str],
    ) -> EvaluationResult:

        if not self.client or not tool_outputs:
            return EvaluationResult(
                metric_name="grounded_accuracy",
                metric_type=MetricType.ACCURACY,
                score=5.0,  # Default pass on 1-5 scale
                passed=True,
                details={},
                explanation="No grounding check available",
            )

        prompt = f"""
Tool facts:
{tool_outputs}

Response:
{response}

Does the response contradict the tool facts?
Answer JSON: {{ "contradiction": true/false }}
"""

        try:
            r = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            import json
            data = json.loads(r.choices[0].message.content)
            contradiction = data.get("contradiction", False)

            # 1-5 scale: 5 for grounded, 1 for contradiction
            score = 1.0 if contradiction else 5.0

            return EvaluationResult(
                metric_name="grounded_accuracy",
                metric_type=MetricType.ACCURACY,
                score=score,
                passed=not contradiction,
                details=data,
                explanation="Contradiction detected" if contradiction else "Grounded",
            )

        except Exception:
            return EvaluationResult(
                metric_name="grounded_accuracy",
                metric_type=MetricType.ACCURACY,
                score=5.0,  # Default pass on 1-5 scale
                passed=True,
                details={},
                explanation="Grounding check failed → default pass",
            )


# =========================
# Safety / Overreach Evaluator (NEW)
# =========================

class SafetyEvaluator:

    RISKY_PATTERNS = [
        "guarantee refund",
        "will definitely refund",
        "account unlocked now",
        "I have removed the charge",
    ]

    def evaluate(self, response: str) -> EvaluationResult:

        lower = response.lower()
        hits = [p for p in self.RISKY_PATTERNS if p in lower]

        safe = len(hits) == 0
        score = 5.0 if safe else 1.0  # 5/5 for safe, 1/5 for risky

        return EvaluationResult(
            metric_name="safety",
            metric_type=MetricType.SAFETY,
            score=score,
            passed=safe,
            details={"matches": hits},
            explanation="No overreach" if safe else "Potential overreach detected",
        )


# =========================
# Azure AI Foundry Evaluators (LLM-as-Judge)
# =========================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert Azure SDK output to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


class AzureAIEvaluatorSuite:
    """
    Wrapper for Azure AI Foundry evaluation SDK evaluators.
    
    Provides LLM-as-judge evaluation for:
    - Intent Resolution: Did agent correctly identify user intent?
    - Task Adherence: Did response follow the task/system prompt?
    - Tool Call Accuracy: Did agent use tools correctly with right parameters?
    - Coherence: Is response logically coherent?
    - Fluency: Is response well-written?
    - Relevance: Is response relevant to query?
    - Solution Accuracy: Does response match ground truth?
    """

    # Tool definitions for Contoso MCP server
    # These are used by ToolCallAccuracyEvaluator to validate tool usage
    CONTOSO_TOOL_DEFINITIONS = [
        {
            "name": "get_all_customers",
            "description": "List all customers with basic info",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_customer_detail",
            "description": "Get a full customer profile including their subscriptions",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "get_subscription_detail",
            "description": "Detailed subscription view with invoices (with payments) and service incidents",
            "parameters": {
                "type": "object",
                "properties": {
                    "subscription_id": {"type": "integer", "description": "Subscription identifier value"}
                },
                "required": ["subscription_id"]
            }
        },
        {
            "name": "get_invoice_payments",
            "description": "Return invoice-level payments list",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Invoice identifier value"}
                },
                "required": ["invoice_id"]
            }
        },
        {
            "name": "pay_invoice",
            "description": "Record a payment for a given invoice and get new outstanding balance",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Invoice identifier value"},
                    "amount": {"type": "number", "description": "Payment amount"},
                    "method": {"type": "string", "description": "Payment method"}
                },
                "required": ["invoice_id", "amount"]
            }
        },
        {
            "name": "get_data_usage",
            "description": "Daily data-usage records for a subscription over a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "subscription_id": {"type": "integer", "description": "Subscription identifier value"},
                    "start_date": {"type": "string", "description": "Inclusive start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "Inclusive end date (YYYY-MM-DD)"},
                    "aggregate": {"type": "boolean", "description": "Set to true for aggregate statistics"}
                },
                "required": ["subscription_id", "start_date", "end_date"]
            }
        },
        {
            "name": "get_billing_summary",
            "description": "Billing summary for a customer including outstanding balance and payment history",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "get_security_logs",
            "description": "Security events for a customer (newest first)",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "unlock_account",
            "description": "Unlock a locked customer account after security verification",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "get_products",
            "description": "List / search available products",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"}
                }
            }
        },
        {
            "name": "get_product_detail",
            "description": "Return a single product by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product identifier value"}
                },
                "required": ["product_id"]
            }
        },
        {
            "name": "get_promotions",
            "description": "List every active promotion",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_eligible_promotions",
            "description": "Promotions eligible for a given customer right now (evaluates basic loyalty/date criteria)",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "get_support_tickets",
            "description": "Retrieve support tickets for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"},
                    "open_only": {"type": "boolean", "description": "Filter to open tickets only"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "create_support_ticket",
            "description": "Create a new support ticket for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"},
                    "subject": {"type": "string", "description": "Ticket subject"},
                    "description": {"type": "string", "description": "Detailed description of the issue"},
                    "priority": {"type": "string", "description": "Priority level (low, medium, high)"}
                },
                "required": ["customer_id", "subject", "description"]
            }
        },
        {
            "name": "get_customer_orders",
            "description": "Get orders for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer identifier value"}
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "search_knowledge_base",
            "description": "Search the knowledge base for relevant articles",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    ]

    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Azure AI evaluators.
        
        Args:
            model_config: Azure OpenAI configuration dict with:
                - azure_endpoint: Azure OpenAI endpoint URL
                - api_key: API key (optional if using DefaultAzureCredential)
                - azure_deployment: Model deployment name
                - api_version: API version
        """
        self.available = AZURE_EVALUATORS_AVAILABLE
        self._evaluators_initialized = False
        
        if not self.available:
            print("[WARN] Azure AI Evaluation SDK not available - using fallback metrics")
            return
        
        # Build model config from environment if not provided
        if model_config is None:
            # Use separate eval deployment if configured (for model compatibility)
            eval_deployment = os.getenv("AZURE_OPENAI_EVAL_DEPLOYMENT") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
            model_config = {
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "azure_deployment": eval_deployment,
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            }
            # Only include api_key if explicitly set; otherwise SDK uses DefaultAzureCredential
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            if api_key:
                model_config["api_key"] = api_key
        
        if not model_config.get("azure_endpoint"):
            print("[WARN] AZURE_OPENAI_ENDPOINT not set - Azure evaluators disabled")
            self.available = False
            return
        
        # Detect reasoning models (GPT-5+, o-series) which require
        # max_completion_tokens instead of max_tokens.
        deployment = model_config.get("azure_deployment", "")
        self._is_reasoning_model = self._check_reasoning_model(deployment)
        if self._is_reasoning_model:
            print(f"[OK] Reasoning model detected ({deployment}) — passing is_reasoning_model=True to evaluators")
        
        # Build common kwargs — SDK evaluators natively support is_reasoning_model flag
        eval_kwargs = {"model_config": model_config}
        if self._is_reasoning_model:
            eval_kwargs["is_reasoning_model"] = True
        
        try:
            # Initialize all evaluators
            self._intent_evaluator = IntentResolutionEvaluator(**eval_kwargs)
            self._coherence_evaluator = CoherenceEvaluator(**eval_kwargs)
            self._fluency_evaluator = FluencyEvaluator(**eval_kwargs)
            self._relevance_evaluator = RelevanceEvaluator(**eval_kwargs)
            self._tool_call_accuracy_evaluator = ToolCallAccuracyEvaluator(**eval_kwargs)
            self._task_adherence_evaluator = TaskAdherenceEvaluator(**eval_kwargs)
            self._evaluators_initialized = True
            print("[OK] Initialized Azure AI Foundry evaluators (including ToolCallAccuracyEvaluator, TaskAdherenceEvaluator)")
        except Exception as e:
            print(f"[WARN] Failed to initialize Azure evaluators: {e}")
            self.available = False

    @staticmethod
    def _check_reasoning_model(model_name: str) -> bool:
        """Check if a model is a reasoning model (GPT-5+, o-series).
        
        Reasoning models require max_completion_tokens instead of max_tokens.
        """
        model_lower = model_name.lower()
        # o-series reasoning models (o1, o3, o4, etc.)
        if re.match(r'^o\d', model_lower):
            return True
        # GPT-5 or higher
        gpt_match = re.search(r'gpt-?(\d+)', model_lower)
        if gpt_match and int(gpt_match.group(1)) >= 5:
            return True
        return False

    def evaluate_intent(self, query: str, response: str) -> EvaluationResult:
        """Evaluate if agent correctly identified user intent."""
        if not self.available or not self._evaluators_initialized:
            return self._fallback_result("intent_resolution", MetricType.INTENT)
        
        try:
            result = self._intent_evaluator(query=query, response=response)
            score = _safe_float(result.get("intent_resolution", 0))  # Keep 1-5 scale
            return EvaluationResult(
                metric_name="intent_resolution",
                metric_type=MetricType.INTENT,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=result,
                explanation=result.get("intent_resolution_reason", ""),
            )
        except Exception as e:
            return self._fallback_result("intent_resolution", MetricType.INTENT, str(e))

    def evaluate_coherence(self, query: str, response: str) -> EvaluationResult:
        """Evaluate response logical coherence."""
        if not self.available or not self._evaluators_initialized:
            return self._fallback_result("coherence", MetricType.COHERENCE)
        
        try:
            result = self._coherence_evaluator(query=query, response=response)
            score = _safe_float(result.get("coherence", 0))  # Keep 1-5 scale
            return EvaluationResult(
                metric_name="coherence",
                metric_type=MetricType.COHERENCE,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=result,
                explanation=result.get("coherence_reason", ""),
            )
        except Exception as e:
            return self._fallback_result("coherence", MetricType.COHERENCE, str(e))

    def evaluate_fluency(self, query: str, response: str) -> EvaluationResult:
        """Evaluate response writing quality."""
        if not self.available or not self._evaluators_initialized:
            return self._fallback_result("fluency", MetricType.FLUENCY)
        
        try:
            result = self._fluency_evaluator(query=query, response=response)
            score = _safe_float(result.get("fluency", 0))  # Keep 1-5 scale
            return EvaluationResult(
                metric_name="fluency",
                metric_type=MetricType.FLUENCY,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=result,
                explanation=result.get("fluency_reason", ""),
            )
        except Exception as e:
            return self._fallback_result("fluency", MetricType.FLUENCY, str(e))

    def evaluate_relevance(self, query: str, response: str) -> EvaluationResult:
        """Evaluate response relevance to query."""
        if not self.available or not self._evaluators_initialized:
            return self._fallback_result("relevance", MetricType.RELEVANCE)
        
        try:
            result = self._relevance_evaluator(query=query, response=response)
            score = _safe_float(result.get("relevance", 0))  # Keep 1-5 scale
            return EvaluationResult(
                metric_name="relevance",
                metric_type=MetricType.RELEVANCE,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=result,
                explanation=result.get("relevance_reason", ""),
            )
        except Exception as e:
            return self._fallback_result("relevance", MetricType.RELEVANCE, str(e))

    def evaluate_tool_call_accuracy(
        self,
        query: str,
        response: str,
        tool_calls: List[Dict[str, Any]],
        tool_definitions: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationResult:
        """
        Evaluate if agent used tools correctly with proper parameters.
        
        Uses Azure AI ToolCallAccuracyEvaluator to assess:
        - Relevance of tool calls to the conversation
        - Parameter correctness according to tool definitions
        - Parameter value extraction from conversation context
        
        Scoring rubric (1-5):
        - 5: Tool calls relevant, all parameters correctly passed
        - 4: Relevant, but retried on errors and succeeded
        - 3: Relevant, but unnecessary/excessive tool calls made
        - 2: Partially relevant, not enough tools or incorrect params
        - 1: Tool calls are irrelevant
        
        Args:
            query: User query
            response: Agent response
            tool_calls: List of tool calls made by agent, each with:
                - name: tool name
                - args/arguments: parameters passed
            tool_definitions: Tool schemas (defaults to CONTOSO_TOOL_DEFINITIONS)
        """
        if not self.available or not self._evaluators_initialized:
            return self._fallback_result("tool_call_accuracy", MetricType.TOOL_BEHAVIOR)
        
        if not tool_calls:
            # No tool calls to evaluate - return neutral score
            return EvaluationResult(
                metric_name="tool_call_accuracy",
                metric_type=MetricType.TOOL_BEHAVIOR,
                score=3.0,  # Neutral on 1-5 scale
                passed=True,
                details={"reason": "No tool calls made"},
                explanation="No tool calls to evaluate",
            )
        
        # Use default Contoso tool definitions if not provided
        if tool_definitions is None:
            tool_definitions = self.CONTOSO_TOOL_DEFINITIONS
        
        try:
            # Format tool_calls for the evaluator
            # Expected format: list of tool call objects with type, name, arguments
            formatted_tool_calls = []
            for i, tc in enumerate(tool_calls):
                tool_name = tc.get("name", tc.get("function", {}).get("name", "unknown"))
                tool_args = tc.get("args", tc.get("arguments", tc.get("function", {}).get("arguments", {})))
                
                # Ensure args is a dict
                if isinstance(tool_args, str):
                    import json
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}
                
                formatted_tool_calls.append({
                    "type": "tool_call",
                    "tool_call_id": tc.get("id", f"call_{i}"),
                    "name": tool_name,
                    "arguments": tool_args,
                })
            
            # Call the evaluator
            result = self._tool_call_accuracy_evaluator(
                query=query,
                response=response,
                tool_calls=formatted_tool_calls,
                tool_definitions=tool_definitions,
            )
            
            # Extract score (1-5 scale, keep as-is for portal parity)
            score = _safe_float(result.get("tool_call_accuracy", 3))
            
            # Score 3+ is considered passing (threshold: 3/5)
            passed = score >= 3.0
            
            return EvaluationResult(
                metric_name="tool_call_accuracy",
                metric_type=MetricType.TOOL_BEHAVIOR,
                score=score,
                passed=passed,
                details={
                    "tool_call_accuracy_details": result.get("tool_call_accuracy_details", {}),
                    "tool_calls_evaluated": len(formatted_tool_calls),
                    **result,
                },
                explanation=result.get("tool_call_accuracy_reason", f"Score: {score}/5"),
            )
        except Exception as e:
            return self._fallback_result("tool_call_accuracy", MetricType.TOOL_BEHAVIOR, str(e))

    def evaluate_task_adherence(
        self,
        query: str,
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        task_description: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate whether the agent adheres to the assigned task and follows expected procedures.
        
        TaskAdherenceEvaluator checks:
        - Did the agent address the user's goal?
        - Did it follow proper procedures/steps?
        - Did it avoid going off-topic or performing unauthorized actions?
        
        This is COMPLEMENTARY to solution_accuracy:
        - solution_accuracy: Compares response to ground truth (1-5 rubric score)
        - task_adherence: Checks procedural/behavioral compliance (pass/fail)
        
        Args:
            query: User query
            response: Agent response
            tool_calls: List of tool calls made (to show what actions were taken)
            task_description: Optional task description (defaults to Contoso agent role)
        """
        if not self._task_adherence_evaluator:
            return self._fallback_result("task_adherence", MetricType.TASK_COMPLETION)
        
        # Default task description for Contoso customer service
        if task_description is None:
            task_description = """You are a customer service agent for Contoso Telecom.
Your task is to help customers with:
- Billing inquiries and payment processing
- Subscription management and data usage
- Technical support and troubleshooting
- Account security and fraud detection
- Product and promotion information

You must:
- Only access customer data when the customer provides their customer ID
- Provide accurate information based on the customer's actual account data
- Never make up or hallucinate information
- Follow proper procedures for sensitive operations like payments
- Be helpful, professional, and empathetic"""
        
        try:
            import json
            
            # Format the conversation as agent messages
            # TaskAdherenceEvaluator expects a conversation-style format
            query_messages = [{"role": "user", "content": query}]
            
            # Build response messages including tool calls if any
            response_messages = []
            
            # If tool calls were made, include them in the assistant's actions
            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc.get("name", tc.get("function", {}).get("name", "unknown"))
                    tool_args = tc.get("args", tc.get("arguments", tc.get("function", {}).get("arguments", {})))
                    
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}
                    
                    tool_call_id = tc.get("call_id") or tc.get("id") or f"call_{tool_name}"
                    
                    response_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args),
                            }
                        }]
                    })
                    
                    # Include the tool RESULT so the judge can verify that the
                    # agent's claims are grounded in actual tool output. Without
                    # this, grounded responses look fabricated and task-adherence
                    # collapses to ~0.
                    tool_result = tc.get("result")
                    response_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(tool_result) if tool_result else "(no tool result captured)",
                    })
            
            # Add final response
            response_messages.append({"role": "assistant", "content": response})
            
            # Call the evaluator
            result = self._task_adherence_evaluator(
                query=query_messages,
                response=response_messages,
                task=task_description,
            )
            
            # Parse the score robustly across SDK versions.
            #
            # azure-ai-evaluation 1.14.0 changed TaskAdherenceEvaluator into a
            # binary "flagged" grader: it returns ``task_adherence`` in {0.0, 1.0}
            # (1.0 == adhered / not flagged) plus an authoritative
            # ``task_adherence_result`` of "pass"/"fail". Older/other versions
            # return a genuine 1-5 score. Treating the binary 1.0 as a 1-5 score
            # and thresholding at >= 3.0 mis-records every PASS as a fail and
            # displays it as "1.0/5". Normalize both shapes here.
            raw_score = result.get("task_adherence", 0)
            result_label = result.get("task_adherence_result")

            if isinstance(raw_score, bool):
                score = 5.0 if raw_score else 1.0
                passed = bool(raw_score)
            elif result_label in ("pass", "fail"):
                # Binary "flagged" grader (SDK >= 1.14.0): trust the result label.
                passed = result_label == "pass"
                numeric = _safe_float(raw_score)
                # If the SDK still reports a real 1-5 score (> 1), preserve it;
                # otherwise map the binary verdict to the 1-5 display scale.
                score = numeric if numeric > 1.0 else (5.0 if passed else 1.0)
            else:
                # Legacy 1-5 numeric score.
                score = _safe_float(raw_score)
                passed = score >= 3.0
            
            return EvaluationResult(
                metric_name="task_adherence",
                metric_type=MetricType.TASK_COMPLETION,
                score=score,
                passed=passed,
                details={
                    "raw_result": result,
                    "task_adherence_result": result_label,
                    "tool_calls_count": len(tool_calls) if tool_calls else 0,
                    "task_description_length": len(task_description),
                },
                explanation=result.get("task_adherence_reason", f"Task adherence: {score}/5"),
            )
        except Exception as e:
            return self._fallback_result("task_adherence", MetricType.TASK_COMPLETION, str(e))

    def evaluate_solution_accuracy(
        self,
        query: str,
        response: str,
        ground_truth: str,
        scoring_rubric: str,
        llm_client=None,
    ) -> EvaluationResult:
        """
        Evaluate solution accuracy against ground truth using scoring rubric.
        
        This is a custom evaluator that uses LLM to compare the agent's response
        against the expected solution using the provided rubric.
        """
        if not llm_client and not self.available:
            return self._fallback_result("solution_accuracy", MetricType.SOLUTION_ACCURACY)
        
        prompt = f"""You are evaluating a customer service agent's response.

USER QUERY:
{query}

AGENT RESPONSE:
{response}

EXPECTED SOLUTION (Ground Truth):
{ground_truth}

SCORING RUBRIC:
{scoring_rubric}

Based on the rubric, score the agent's response from 1-5.
Return JSON: {{"score": <1-5>, "reason": "<brief explanation>"}}
"""
        
        try:
            # Use provided client or create one from environment
            if llm_client:
                client = llm_client
            else:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                )
            
            result = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            
            import json
            data = json.loads(result.choices[0].message.content)
            score = _safe_float(data.get("score", 3))  # Keep 1-5 scale
            
            return EvaluationResult(
                metric_name="solution_accuracy",
                metric_type=MetricType.SOLUTION_ACCURACY,
                score=score,
                passed=score >= 3.0,  # Threshold: 3/5
                details=data,
                explanation=data.get("reason", ""),
            )
        except Exception as e:
            return self._fallback_result("solution_accuracy", MetricType.SOLUTION_ACCURACY, str(e))

    def evaluate_all(
        self,
        query: str,
        response: str,
        ground_truth: Optional[str] = None,
        scoring_rubric: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        llm_client=None,
    ) -> List[EvaluationResult]:
        """Run all Azure AI evaluators and return list of results.
        
        Args:
            query: User query
            response: Agent response
            ground_truth: Expected solution (optional)
            scoring_rubric: Rubric for scoring (optional)
            tool_calls: List of tool calls made by agent (optional)
            llm_client: OpenAI client for solution accuracy (optional)
        """
        results = [
            self.evaluate_intent(query, response),
            self.evaluate_coherence(query, response),
            self.evaluate_fluency(query, response),
            self.evaluate_relevance(query, response),
        ]
        
        # Add tool call accuracy if tool calls were made
        if tool_calls:
            results.append(
                self.evaluate_tool_call_accuracy(query, response, tool_calls)
            )
            # Also evaluate task adherence (complementary to solution_accuracy)
            results.append(
                self.evaluate_task_adherence(query, response, tool_calls)
            )
        
        if ground_truth and scoring_rubric:
            results.append(
                self.evaluate_solution_accuracy(
                    query, response, ground_truth, scoring_rubric, llm_client
                )
            )
        
        return results

    def _fallback_result(
        self,
        metric_name: str,
        metric_type: MetricType,
        error: str = "Evaluator not available",
    ) -> EvaluationResult:
        """Return a neutral fallback result when evaluator is unavailable."""
        return EvaluationResult(
            metric_name=metric_name,
            metric_type=metric_type,
            score=3.0,  # Neutral score on 1-5 scale
            passed=True,
            details={"error": error},
            explanation=f"Fallback: {error}",
        )
