import json
import logging
from typing import Any, Dict, List

from agent_framework import AgentThread, ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from agents.base_agent import BaseAgent, ToolCallTrackingMixin

logger = logging.getLogger(__name__)

class Agent(ToolCallTrackingMixin, BaseAgent):
    """Agent Framework implementation with Primary Agent + Reviewer reflection workflow and MCP streaming."""

    def __init__(self, state_store: Dict[str, Any], session_id: str, access_token: str | None = None) -> None:
        super().__init__(state_store, session_id)
        self._primary_agent: ChatAgent | None = None
        self._reviewer: ChatAgent | None = None
        self._thread: AgentThread | None = None
        self._initialized = False
        self._access_token = access_token
        self._ws_manager = None  # WebSocket manager for streaming
        # Track conversation turn for tool call grouping - load from state store
        self._turn_key = f"{session_id}_current_turn"
        self._current_turn = state_store.get(self._turn_key, 0)
        self.init_tool_tracking()
        
        # Log that reflection agent is being used
        print(f"REFLECTION AGENT INITIALIZED - Session: {session_id}")
        logger.info(f"REFLECTION AGENT INITIALIZED - Session: {session_id}")

    def set_websocket_manager(self, manager: Any) -> None:
        """Allow backend to inject WebSocket manager for streaming events."""
        self._ws_manager = manager
        logger.info(f"[STREAMING] WebSocket manager set for reflection_agent, session_id={self.session_id}")

    def _extract_refined_content(self, response: str) -> str:
        """
        Extract refined content from agent response, avoiding internal communication.
        Based on teammate feedback to ensure clean content extraction.
        """
        # Look for structured content markers
        if "##REFINED_CONTENT:" in response and "##END" in response:
            try:
                # Extract content between markers
                start_marker = "##REFINED_CONTENT:"
                end_marker = "##END"
                start_idx = response.find(start_marker) + len(start_marker)
                end_idx = response.find(end_marker)
                if start_idx > len(start_marker) - 1 and end_idx > start_idx:
                    extracted = response[start_idx:end_idx].strip()
                    print(f"[PARSING] Successfully extracted refined content: {len(extracted)} chars")
                    return extracted
            except Exception as e:
                print(f"[PARSING] Error extracting structured content: {e}")
        
        # Fallback: return full response if no structured format found
        print(f"[PARSING] No structured format found, using full response")
        return response

    async def _setup_reflection_agents(self) -> None:
        if self._initialized:
            return

        if not all([self.azure_deployment, self.azure_openai_endpoint, self.api_version]):
            raise RuntimeError(
                "Azure OpenAI configuration is incomplete. Ensure "
                "AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_API_VERSION are set."
            )
        if not self.azure_openai_key and not self.azure_credential:
            raise RuntimeError(
                "Azure OpenAI authentication is not configured. Either set "
                "AZURE_OPENAI_API_KEY or ensure managed identity is available."
            )

        headers = self._build_headers()
        mcp_tools = await self._maybe_create_tools(headers)

        if self.azure_openai_key:
            chat_client = AzureOpenAIChatClient(
                api_key=self.azure_openai_key,
                deployment_name=self.azure_deployment,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )
        else:
            chat_client = AzureOpenAIChatClient(
                credential=self.azure_credential,
                deployment_name=self.azure_deployment,
                endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
            )

        tools = mcp_tools[0] if mcp_tools else None

        # Primary Agent - Customer Support Agent with MCP tools
        self._primary_agent = ChatAgent(
            name="PrimaryAgent",
            chat_client=chat_client,
            instructions="You are a helpful customer support assistant for Contoso company. You can help with billing, promotions, security, account information, and other customer inquiries. "
                "Use the available MCP tools to look up customer information, billing details, promotions, and security settings. "
                "When a customer provides an ID or asks about their account, use the tools to retrieve accurate, up-to-date information. "
                "If the user input is just an ID or feels incomplete, review previous communication in the same session and infer the user's intent based on context. "
                "For example, if they ask about billing and then provide an ID, assume they want billing information for that ID. "
                "Always be helpful, professional, and provide detailed information when available. "
                "\n\nIMPORTANT: When responding to reviewer feedback for refinement, format your response exactly as follows:\n"
                "##REFINED_CONTENT:\n"
                "[Your improved response here]\n"
                "##END\n"
                "This ensures clean content extraction without mixing internal communication with the final response.",
            tools=tools,
            model=self.openai_model_name,
        )

        # Reviewer Agent - Quality assurance for customer support responses
        self._reviewer = ChatAgent(
            name="Reviewer",
            chat_client=chat_client,
            instructions="You are a quality assurance reviewer for customer support responses. "
                "Review the customer support agent's response for accuracy, completeness, helpfulness, and professionalism. "
                "Check if all customer questions were addressed and if the information provided is clear and useful. "
                "Provide constructive feedback if improvements are needed, or respond with 'APPROVE' if the response meets quality standards. "
                "Focus on: 1) Accuracy of information, 2) Completeness of answer, 3) Professional tone, 4) Proper use of available tools.",
            tools=tools,
            model=self.openai_model_name,
        )

        try:
            await self._primary_agent.__aenter__()
            await self._reviewer.__aenter__()
        except Exception:
            self._primary_agent = None
            self._reviewer = None
            raise

        if self.state:
            self._thread = await self._primary_agent.deserialize_thread(self.state)
        else:
            self._thread = self._primary_agent.get_new_thread()

        self._initialized = True

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _maybe_create_tools(self, headers: Dict[str, str]) -> List[MCPStreamableHTTPTool] | None:
        if not self.mcp_server_uri:
            logger.warning("MCP_SERVER_URI not configured; agents run without MCP tools.")
            return None
        return [MCPStreamableHTTPTool(
            name="mcp-streamable",
            url=self.mcp_server_uri,
            headers=headers,
            timeout=30,
            request_timeout=30,
        )]

    async def chat_async(self, prompt: str) -> str:
        """Run Primary Agent → Reviewer → Primary Agent refinement pipeline for customer support."""
        print(f"REFLECTION AGENT chat_async called with prompt: {prompt[:50]}...")
        logger.info(f"REFLECTION AGENT chat_async called with prompt: {prompt[:50]}...")
        
        await self._setup_reflection_agents()
        if not (self._primary_agent and self._reviewer and self._thread):
            raise RuntimeError("Agents not initialized correctly.")

        self._current_turn += 1
        self.state_store[self._turn_key] = self._current_turn

        # Use streaming if WebSocket manager is available
        if self._ws_manager:
            print(f"REFLECTION AGENT: Using STREAMING path")
            logger.info(f"REFLECTION AGENT: Using STREAMING path")
            return await self._chat_async_streaming(prompt)
        
        # Non-streaming path (fallback)
        print(f"REFLECTION AGENT: Using NON-STREAMING path")
        logger.info(f"REFLECTION AGENT: Using NON-STREAMING path")
        return await self._chat_async_non_streaming(prompt)

    async def _chat_async_streaming(self, prompt: str) -> str:
        """Handle reflection workflow with streaming support via WebSocket."""
        
        print(f"STREAMING: Starting reflection workflow for: {prompt[:50]}...")
        logger.info(f"STREAMING: Starting reflection workflow for: {prompt[:50]}...")
        
        # Notify UI that reflection workflow is starting
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "orchestrator",
                    "kind": "plan", 
                    "content": "Reflection Workflow Starting\n\nInitiating Primary Agent → Reviewer → Refinement pipeline for optimal response quality...",
                },
            )
            
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "agent_start",
                    "agent_id": "primary_agent",
                    "show_message_in_internal_process": True,
                },
            )

        # Step 1: Primary Agent (Customer Support) handles the customer inquiry
        print(f"STREAMING STEP 1: Primary Agent processing customer inquiry")
        logger.info(f"STREAMING STEP 1: Primary Agent processing customer inquiry")
        
        # Notify UI about Step 1
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "orchestrator",
                    "kind": "progress",
                    "content": "Primary Agent Analysis\n\nAnalyzing your request and gathering information using available tools...",
                },
            )

        # Stream Step 1 response
        step1_response = []
        try:
            async for chunk in self._primary_agent.run_stream(prompt, thread=self._thread):
                # Process contents for tool calls
                if hasattr(chunk, 'contents') and chunk.contents:
                    for content in chunk.contents:
                        if content.type == "function_call":
                            if getattr(content, 'name', None):
                                self.add_tool_call(content.name, {})
                            if self._ws_manager:
                                await self._ws_manager.broadcast(
                                    self.session_id,
                                    {
                                        "type": "tool_called",
                                        "agent_id": "primary_agent",
                                        "tool_name": content.name,
                                    },
                                )
                
                # Extract and stream text
                if hasattr(chunk, 'text') and chunk.text:
                    step1_response.append(chunk.text)
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "agent_token",
                                "agent_id": "primary_agent",
                                "content": chunk.text,
                            },
                        )
        except Exception as exc:
            logger.error("[REFLECTION] Error during Step 1 streaming: %s", exc, exc_info=True)
            raise

        initial_response = ''.join(step1_response)

        # Step 2: Reviewer checks the customer support response
        print(f"STREAMING STEP 2: Reviewer evaluating response quality")
        logger.info(f"STREAMING STEP 2: Reviewer evaluating response quality")
        
        # Send complete primary agent response
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "agent_message",
                    "agent_id": "primary_agent", 
                    "role": "assistant",
                    "content": initial_response,
                },
            )
        
        # Notify UI about moving to review phase
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "orchestrator",
                    "kind": "progress",
                    "content": "Quality Reviewer Analysis\n\nReviewer is evaluating the Primary Agent's response for accuracy, completeness, and professional tone...",
                },
            )
            
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "agent_start",
                    "agent_id": "reviewer_agent",
                    "show_message_in_internal_process": True,
                },
            )

        feedback_request = f"Please review this customer support response for accuracy, completeness, and professionalism:\n\nCustomer Question: {prompt}\n\nAgent Response: {initial_response}"
        
        # Stream reviewer feedback
        feedback_response = []
        try:
            async for chunk in self._reviewer.run_stream(feedback_request, thread=self._thread):
                # Extract and stream text
                if hasattr(chunk, 'text') and chunk.text:
                    feedback_response.append(chunk.text)
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            self.session_id,
                            {
                                "type": "agent_token",
                                "agent_id": "reviewer_agent",
                                "content": chunk.text,
                            },
                        )
        except Exception as exc:
            logger.error("[REFLECTION] Error during reviewer streaming: %s", exc, exc_info=True)
            raise

        feedback_result_text = ''.join(feedback_response)
        
        # Send complete reviewer response
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "agent_message",
                    "agent_id": "reviewer_agent",
                    "role": "assistant", 
                    "content": feedback_result_text,
                },
            )

        # Step 3: Determine if refinement is needed
        if "APPROVE" not in feedback_result_text.upper():
            print(f"STREAMING STEP 3: REFINEMENT NEEDED - Primary Agent improving response")
            logger.info(f"STREAMING STEP 3: REFINEMENT NEEDED - Primary Agent improving response")
            
            # Notify UI about Step 3 - refinement
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "orchestrator",
                        "kind": "progress",
                        "content": "Response Refinement\n\nReviewer suggested improvements. Primary Agent is now refining the response based on feedback...",
                    },
                )
                
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "agent_start",
                        "agent_id": "primary_agent_refinement",
                        "show_message_in_internal_process": True,
                    },
                )

            refinement_request = f"""Please improve your customer support response based on this feedback:

Original Question: {prompt}

Your Response: {initial_response}

Reviewer Feedback: {feedback_result_text}

IMPORTANT: Format your refined response exactly as follows:
##REFINED_CONTENT:
[Your improved response here]
##END

Do not include phrases like "Thank you for the feedback" or other meta-commentary. Place only the refined customer support response between the markers."""
            
            # Stream refinement response
            refinement_response = []
            try:
                async for chunk in self._primary_agent.run_stream(refinement_request, thread=self._thread):
                    # Process contents for tool calls
                    if hasattr(chunk, 'contents') and chunk.contents:
                        for content in chunk.contents:
                            if content.type == "function_call":
                                if getattr(content, 'name', None):
                                    self.add_tool_call(content.name, {})
                                if self._ws_manager:
                                    await self._ws_manager.broadcast(
                                        self.session_id,
                                        {
                                            "type": "tool_called",
                                            "agent_id": "primary_agent_refinement",
                                            "tool_name": content.name,
                                        },
                                    )
                    
                    # Extract and stream text
                    if hasattr(chunk, 'text') and chunk.text:
                        refinement_response.append(chunk.text)
                        if self._ws_manager:
                            await self._ws_manager.broadcast(
                                self.session_id,
                                {
                                    "type": "agent_token",
                                    "agent_id": "primary_agent_refinement",
                                    "content": chunk.text,
                                },
                            )
            except Exception as exc:
                logger.error("[REFLECTION] Error during Step 3 streaming: %s", exc, exc_info=True)
                raise

            raw_refinement_response = ''.join(refinement_response)
            
            # Extract clean content using structured parsing (addresses teammate feedback)
            assistant_response = self._extract_refined_content(raw_refinement_response)
            
            print(f"STREAMING STEP 3: Content extraction - Original: {len(raw_refinement_response)} chars, Extracted: {len(assistant_response)} chars")
            logger.info(f"STREAMING STEP 3: Content extraction - Original: {len(raw_refinement_response)} chars, Extracted: {len(assistant_response)} chars")
            
            # Send complete refinement response
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "agent_message",
                        "agent_id": "primary_agent_refinement",
                        "role": "assistant",
                        "content": assistant_response,
                    },
                )
        else:
            print(f"STREAMING STEP 3: APPROVED - Response approved by reviewer")
            logger.info(f"STREAMING STEP 3: APPROVED - Response approved by reviewer")
            
            # Notify UI about approval
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    self.session_id,
                    {
                        "type": "orchestrator",
                        "kind": "result",
                        "content": "Quality Approved\n\nReviewer has approved the Primary Agent's response! No refinement needed.",
                    },
                )
            
            assistant_response = initial_response

        # Send final result with reflection summary
        reflection_summary = "Reflection Process Complete\n\n"
        reflection_summary += "• Primary Agent: Analyzed request and gathered information\n"
        reflection_summary += "• Quality Reviewer: Evaluated response for accuracy and completeness\n"
        if "APPROVE" not in feedback_result_text.upper():
            reflection_summary += "• Refinement: Response improved based on reviewer feedback\n"
        else:
            reflection_summary += "• Approval: Response met quality standards on first attempt\n"
        reflection_summary += "\nFinal response delivered with enhanced quality assurance!"
        
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "orchestrator",
                    "kind": "result",
                    "content": reflection_summary,
                },
            )
            
        if self._ws_manager:
            await self._ws_manager.broadcast(
                self.session_id,
                {
                    "type": "final_result",
                    "content": assistant_response,
                },
            )

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)

        new_state = await self._thread.serialize()
        self._setstate(new_state)

        return assistant_response

    async def _chat_async_non_streaming(self, prompt: str) -> str:
        """Handle reflection workflow without streaming (fallback)."""
        
        # Step 1: Primary Agent (Customer Support) handles the customer inquiry
        logger.info(f"[REFLECTION] ===============================================")
        logger.info(f"[REFLECTION] STEP 1: Primary Agent processing customer inquiry")
        logger.info(f"[REFLECTION] Session: {self.session_id}, Turn: {self._current_turn}")
        logger.info(f"[REFLECTION] Customer Question: {prompt}")
        logger.info(f"[REFLECTION] ===============================================")
        
        initial_result = await self._primary_agent.run(prompt, thread=self._thread)
        
        logger.info(f"[REFLECTION] ===============================================")
        logger.info(f"[REFLECTION] STEP 1 COMPLETED: Primary Agent Response Generated")
        logger.info(f"[REFLECTION] Response Length: {len(initial_result.text)} characters")
        logger.info(f"[REFLECTION] Response Preview: {initial_result.text[:200]}...")
        logger.info(f"[REFLECTION] ===============================================")

        # Step 2: Reviewer checks the customer support response
        logger.info(f"[REFLECTION] ===============================================")
        logger.info(f"[REFLECTION] STEP 2: Reviewer evaluating response quality")
        logger.info(f"[REFLECTION] Sending Primary Agent's response to Reviewer...")
        logger.info(f"[REFLECTION] ===============================================")
        
        feedback_request = f"Please review this customer support response for accuracy, completeness, and professionalism:\n\nCustomer Question: {prompt}\n\nAgent Response: {initial_result.text}"
        feedback = await self._reviewer.run(feedback_request, thread=self._thread)
        
        logger.info(f"[REFLECTION] ===============================================")
        logger.info(f"[REFLECTION] STEP 2 COMPLETED: Reviewer Feedback Generated")
        logger.info(f"[REFLECTION] Feedback Length: {len(feedback.text)} characters")
        logger.info(f"[REFLECTION] Feedback Preview: {feedback.text[:200]}...")
        logger.info(f"[REFLECTION] Contains 'APPROVE': {'APPROVE' in feedback.text.upper()}")
        logger.info(f"[REFLECTION] ===============================================")

        # Step 3: Primary Agent refines response based on feedback (if needed)
        if "APPROVE" not in feedback.text.upper():
            logger.info(f"[REFLECTION] ===============================================")
            logger.info(f"[REFLECTION] STEP 3: REFINEMENT NEEDED - Primary Agent improving response")
            logger.info(f"[REFLECTION] Reviewer suggested improvements, sending back to Primary Agent...")
            logger.info(f"[REFLECTION] ===============================================")
            
            refinement_request = f"""Please improve your customer support response based on this feedback:

Original Question: {prompt}

Your Response: {initial_result.text}

Reviewer Feedback: {feedback.text}

IMPORTANT: Format your refined response exactly as follows:
##REFINED_CONTENT:
[Your improved response here]
##END

Do not include phrases like "Thank you for the feedback" or other meta-commentary. Place only the refined customer support response between the markers."""
            final_result = await self._primary_agent.run(refinement_request, thread=self._thread)
            raw_response = final_result.text
            assistant_response = self._extract_refined_content(raw_response)
            
            logger.info(f"[REFLECTION] ===============================================")
            logger.info(f"[REFLECTION] STEP 3 COMPLETED: Primary Agent Refined Response")
            logger.info(f"[REFLECTION] Refined Response Length: {len(assistant_response)} characters")
            logger.info(f"[REFLECTION] Refined Response Preview: {assistant_response[:200]}...")
            logger.info(f"[REFLECTION] ===============================================")
        else:
            logger.info(f"[REFLECTION] ===============================================")
            logger.info(f"[REFLECTION] STEP 3: APPROVAL - No refinement needed")
            logger.info(f"[REFLECTION] Reviewer approved the response, using original response")
            logger.info(f"[REFLECTION] ===============================================")
            assistant_response = initial_result.text

        logger.info(f"[REFLECTION] ===============================================")
        logger.info(f"[REFLECTION] REFLECTION WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info(f"[REFLECTION] Final Response Length: {len(assistant_response)} characters")
        logger.info(f"[REFLECTION] Agents Involved: Primary Agent + Reviewer")
        logger.info(f"[REFLECTION] Refinement Required: {'Yes' if 'APPROVE' not in feedback.text.upper() else 'No'}")
        logger.info(f"[REFLECTION] ===============================================")

        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant_response},
        ]
        self.append_to_chat_history(messages)

        new_state = await self._thread.serialize()
        self._setstate(new_state)

        return assistant_response
        self.append_to_chat_history(messages)

        new_state = await self._thread.serialize()
        self._setstate(new_state)

        return assistant_response
