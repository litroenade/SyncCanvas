"""
AI Engine Core: Base Agent
Defines the abstract base class for all agents in the system.
Handles memory, state, tool execution, and LLM interaction loops.
"""

from __future__ import annotations

import json
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from openai.types.chat import ChatCompletionMessageParam

from src.ai_engine.core.llm import LLMClient, LLMResponse
from src.db.models import AgentAction, AgentRun
from src.logger import get_logger
from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


class AgentContext:
    """
    Context object passed around during an agent's execution.
    Holds references to the run ID, shared state, etc.
    """
    def __init__(self, run_id: int, session_id: str, user_id: Optional[str] = None):
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = user_id
        self.shared_state: Dict[str, Any] = {}


class BaseAgent(ABC):
    """
    Abstract Base Agent.
    """

    def __init__(
        self,
        name: str,
        role: str,
        llm_client: LLMClient,
        run_service: AgentRunService,
        system_prompt: str
    ):
        self.name = name
        self.role = role
        self.llm = llm_client
        self.run_service = run_service
        self.system_prompt = system_prompt
        self.tools: Dict[str, Any] = {}
        self.tool_definitions: List[Dict[str, Any]] = []

    def register_tool(self, name: str, func: Any, schema: Dict[str, Any]):
        """Register a tool for the agent to use."""
        self.tools[name] = func
        self.tool_definitions.append(schema)

    async def run(self, context: AgentContext, user_input: str) -> str:
        """
        Main execution entry point.
        """
        logger.info(f"Agent {self.name} starting run {context.run_id}")
        
        # 1. Initialize Memory / Messages
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

        # 2. Main Loop (Think -> Act -> Observe)
        max_turns = 10
        current_turn = 0
        final_response = ""

        while current_turn < max_turns:
            current_turn += 1
            
            # 2.1 Think (Call LLM)
            try:
                response: LLMResponse = await self.llm.chat_completion(
                    messages=messages,
                    tools=self.tool_definitions if self.tool_definitions else None,
                    tool_choice="auto" if self.tool_definitions else "none"
                )
            except Exception as e:
                logger.error(f"LLM Error in agent {self.name}: {e}")
                await self._log_action(context, "error", f"LLM Call Failed: {str(e)}")
                return "I encountered an error while processing your request."

            # 2.2 Log Thought
            await self._log_action(
                context, 
                "thought", 
                response.content, 
                metadata={"model": response.model, "provider": response.provider}
            )
            
            # Append assistant message
            messages.append({
                "role": "assistant", 
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"]
                    } for tc in response.tool_calls
                ] if response.tool_calls else None
            })

            # 2.3 Act (Execute Tools)
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    func_name = tool_call["function"]["name"]
                    func_args_str = tool_call["function"]["arguments"]
                    call_id = tool_call["id"]
                    
                    tool_result_str = ""
                    try:
                        func_args = json.loads(func_args_str)
                        
                        # Log Tool Call
                        await self._log_action(
                            context, 
                            "tool_call", 
                            f"Calling {func_name}", 
                            metadata={"args": func_args, "tool_id": call_id}
                        )

                        # Execute
                        if func_name in self.tools:
                            result = await self._execute_tool(func_name, func_args, context)
                            tool_result_str = json.dumps(result, ensure_ascii=False)
                        else:
                            tool_result_str = f"Error: Tool {func_name} not found."

                    except Exception as e:
                        tool_result_str = f"Error executing tool {func_name}: {str(e)}\n{traceback.format_exc()}"
                        logger.error(f"Tool Execution Error: {e}")

                    # Log Tool Result
                    await self._log_action(
                        context, 
                        "tool_result", 
                        tool_result_str[:500] + "..." if len(tool_result_str) > 500 else tool_result_str,
                        metadata={"tool_id": call_id}
                    )

                    # Append tool output to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result_str
                    })
                
                # Loop continues to let LLM process the tool result
                continue
            
            # 2.4 Final Response (No tool calls)
            final_response = response.content
            break

        return final_response

    async def _execute_tool(self, name: str, args: Dict[str, Any], context: AgentContext) -> Any:
        """Execute a registered tool."""
        func = self.tools[name]
        # Check if tool accepts context
        # For simplicity, we assume tools might need context if designed for it, 
        # but here we'll just pass args. 
        # In a more advanced version, we'd inspect the signature.
        if hasattr(func, "__code__") and "context" in func.__code__.co_varnames:
             return await func(**args, context=context)
        return await func(**args)

    async def _log_action(self, context: AgentContext, action_type: str, content: str, metadata: Dict[str, Any] = None):
        """Helper to log actions to DB."""
        try:
            await self.run_service.log_action(
                run_id=context.run_id,
                action_type=action_type,
                content=content,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to log action: {e}")

