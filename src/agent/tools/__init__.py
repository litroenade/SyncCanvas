"""AI 工具集合

导入所有工具模块以注册到全局工具注册表。
"""

# 导入工具模块以触发 @registry.register 装饰器
from src.agent.tools import excalidraw_tools
from src.agent.tools import web_tools
from src.agent.tools import general_tools
from src.agent.tools import text_tools

__all__ = [
    "excalidraw_tools",
    "web_tools", 
    "general_tools",
    "text_tools",
]

