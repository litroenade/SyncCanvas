"""
AI Engine Agent: Teacher Agent
The primary orchestrator. It understands user intent, manages the conversation,
and delegates drawing tasks to the Painter Agent or uses tools directly.
"""

from typing import Any, Dict, List

from src.ai_engine.core.agent import BaseAgent, AgentContext
from src.ai_engine.core.llm import LLMClient
from src.ai_engine.core.tools import registry
from src.services.agent_runs import AgentRunService
from src.ai_engine.agents.painter import PainterAgent
# Import tools to ensure they are registered
import src.ai_engine.tools.excalidraw_tools  # noqa: 加载 Excalidraw 工具
import src.ai_engine.tools.knowledge_tools  # noqa

TEACHER_SYSTEM_PROMPT = """
You are an expert AI Tutor and Whiteboard Assistant.
Your goal is to help the user learn by explaining concepts clearly and, when helpful, 
visualizing them on the whiteboard.

You have access to a set of tools to manipulate the whiteboard.
If the user asks to draw something, use the appropriate tools.
If the user asks a question, answer it clearly.
If the request is complex, break it down into steps.

You are the "Teacher". You control the flow.
"""

class TeacherAgent(BaseAgent):
    def __init__(
        self,
        llm_client: LLMClient,
        run_service: AgentRunService
    ):
        super().__init__(
            name="Teacher",
            role="Orchestrator",
            llm_client=llm_client,
            run_service=run_service,
            system_prompt=TEACHER_SYSTEM_PROMPT
        )
        self.painter = PainterAgent(llm_client, run_service)
        self._register_default_tools()

    def _register_default_tools(self):
        # Load all tools from registry for the Teacher
        # Teacher can use knowledge/search tools and basic board tools when trivial.
        for name, func in registry.get_all_tools().items():
            schema = registry._schemas.get(name)
            if schema:
                self.register_tool(name, func, schema)

    async def run(self, context: AgentContext, user_input: str) -> str:
        # If request is clearly drawing-heavy, hand off to Painter Agent directly
        if self._should_delegate_to_painter(user_input):
            await self._log_action(context, "handoff", "Delegating to painter", {"target": "painter"})
            return await self.painter.run(context, user_input)

        return await super().run(context, user_input)

    def _should_delegate_to_painter(self, text: str) -> bool:
        lowered = text.lower()
        draw_keywords = ["draw", "diagram", "flowchart", "sketch", "layout", "uml", "erd", "graph", "visualize", "paint", "illustrate", "画", "绘制"]
        return any(k in lowered for k in draw_keywords)
