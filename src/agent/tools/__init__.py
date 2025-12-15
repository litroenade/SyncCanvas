"""包名称: tools
功能说明: Agent 可用工具集

核心工具模块:
- flowchart: create_flowchart_node, connect_nodes (2)
- elements: list_elements, delete_elements, batch_create_elements... (7)
- canvas: get_canvas_bounds (1)
- general_tools: get_current_time, calculate (2)
- web_tools: fetch_webpage (1)

总计约 13 个工具
"""

# 画布工具
from src.agent.tools import flowchart  # noqa: F401
from src.agent.tools import elements  # noqa: F401
from src.agent.tools import canvas  # noqa: F401

# 通用工具
from src.agent.tools import general_tools  # noqa: F401
from src.agent.tools import web_tools  # noqa: F401

# 元素预设常量
ELEMENT_PRESETS = {
    "flowchart_start": {
        "node_type": "ellipse",
        "width": 120,
        "height": 50,
        "stroke_color": "#1e1e1e",
        "bg_color": "#e6f7ff",
    },
    "flowchart_end": {
        "node_type": "ellipse",
        "width": 120,
        "height": 50,
        "stroke_color": "#1e1e1e",
        "bg_color": "#fff1f0",
    },
    "flowchart_process": {
        "node_type": "rectangle",
        "width": 160,
        "height": 70,
        "stroke_color": "#1e1e1e",
        "bg_color": "#ffffff",
    },
    "flowchart_decision": {
        "node_type": "diamond",
        "width": 120,
        "height": 120,
        "stroke_color": "#1e1e1e",
        "bg_color": "#fff7e6",
    },
}

__all__ = [
    "flowchart",
    "elements",
    "canvas",
    "general_tools",
    "web_tools",
    "ELEMENT_PRESETS",
]
