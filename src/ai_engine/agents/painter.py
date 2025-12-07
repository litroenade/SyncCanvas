"""
AI Engine Agent: Painter Agent
Specialized agent for visual tasks. It translates high-level visual descriptions
into concrete whiteboard operations (shapes, connectors, text).

使用 Excalidraw 作为画布引擎，支持流程图节点和绑定箭头。
"""

from typing import Any, Dict

from src.ai_engine.core.agent import BaseAgent, AgentContext
from src.ai_engine.core.llm import LLMClient
from src.ai_engine.core.tools import registry
from src.services.agent_runs import AgentRunService
import src.ai_engine.tools.excalidraw_tools  # noqa: 加载 Excalidraw 工具

PAINTER_SYSTEM_PROMPT = """
You are the Painter Agent, an expert in technical illustration and diagramming.
Your sole responsibility is to update the whiteboard based on instructions.

You do NOT explain concepts. You only DRAW.

Available tools:
- create_flowchart_node: Create flowchart nodes (rectangle for process, diamond for decision, ellipse for start/end)
- connect_nodes: Connect two nodes with an arrow (supports labels like 'Yes', 'No')
- create_element: Create basic Excalidraw elements
- list_elements: List current elements on the canvas
- update_element: Update element properties
- delete_elements: Delete elements by ID
- clear_canvas: Clear all elements

Layout guidelines:
- Start from top (y=0) and flow downward. Each subsequent node should increase Y by ~150px.
- For branches (Yes/No), offset X by +/-200px.
- Use precise coordinates and be consistent with spacing.
"""

class PainterAgent(BaseAgent):
    def __init__(
        self,
        llm_client: LLMClient,
        run_service: AgentRunService
    ):
        super().__init__(
            name="Painter",
            role="Visualizer",
            llm_client=llm_client,
            run_service=run_service,
            system_prompt=PAINTER_SYSTEM_PROMPT
        )
        self._register_default_tools()

    def _register_default_tools(self):
        # Load all tools from registry for the Painter
        for name, func in registry.get_all_tools().items():
            schema = registry._schemas.get(name)
            if schema:
                self.register_tool(name, func, schema)
