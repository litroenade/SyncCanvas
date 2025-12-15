"""包名称: tools
功能说明: Agent 可用工具集

包含 Agent 可调用的各类画布和通用工具。

工具模块:
- flowchart: 流程图节点和连接
- elements: 基础元素 CRUD
- canvas: 画布状态查询
- architecture: 架构图容器和组件
- presets: 元素预设和批量操作
- general_tools: 通用工具
- web_tools: 网络工具
- text_tools: 文本工具
- auto_layout: 自动布局
- sequence: 时序图工具
"""

# 导入工具模块以触发 @registry.register 装饰器
from src.agent.tools import flowchart  # noqa: F401
from src.agent.tools import elements  # noqa: F401
from src.agent.tools import canvas  # noqa: F401
from src.agent.tools import architecture  # noqa: F401
from src.agent.tools import presets  # noqa: F401
from src.agent.tools import general_tools  # noqa: F401
from src.agent.tools import web_tools  # noqa: F401
from src.agent.tools import text_tools  # noqa: F401
from src.agent.tools import auto_layout  # noqa: F401
from src.agent.tools import sequence  # noqa: F401

# 导出预设
from src.agent.tools.presets import ELEMENT_PRESETS

__all__ = [
    "flowchart",
    "elements",
    "canvas",
    "architecture",
    "presets",
    "general_tools",
    "web_tools",
    "text_tools",
    "auto_layout",
    "sequence",
    "ELEMENT_PRESETS",
]
