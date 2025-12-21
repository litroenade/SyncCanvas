"""包名称: tools
功能说明: Agent 可用工具集
"""

# 画布工具
from src.agent.tools import flowchart  # noqa: F401
from src.agent.tools import elements  # noqa: F401
from src.agent.tools import canvas  # noqa: F401
from src.agent.tools import library  # noqa: F401

# 通用工具
from src.agent.tools import general_tools  # noqa: F401
from src.agent.tools import web_tools  # noqa: F401

from src.agent.tools.helpers import get_theme_colors


def get_element_presets(theme: str = "light") -> dict:
    """获取元素预设 (带主题色)

    Args:
        theme: 主题名称 ("light" | "dark")

    Returns:
        dict: 预设配置
    """
    colors = get_theme_colors(theme)
    return {
        "flowchart_start": {
            "node_type": "ellipse",
            "width": 120,
            "height": 50,
            "stroke_color": colors["stroke"],
            "bg_color": "#e6f7ff" if theme == "light" else "#1e3a5f",
        },
        "flowchart_end": {
            "node_type": "ellipse",
            "width": 120,
            "height": 50,
            "stroke_color": colors["stroke"],
            "bg_color": "#fff1f0" if theme == "light" else "#5f1e1e",
        },
        "flowchart_process": {
            "node_type": "rectangle",
            "width": 160,
            "height": 70,
            "stroke_color": colors["stroke"],
            "bg_color": colors["background"],
        },
        "flowchart_decision": {
            "node_type": "diamond",
            "width": 120,
            "height": 120,
            "stroke_color": colors["stroke"],
            "bg_color": "#fff7e6" if theme == "light" else "#5f4a1e",
        },
    }


# 保留向后兼容
ELEMENT_PRESETS = get_element_presets("light")

__all__ = [
    "flowchart",
    "elements",
    "canvas",
    "general_tools",
    "web_tools",
    "get_element_presets",
    "ELEMENT_PRESETS",
]

