"""包名称: agents
功能说明: Agent 实现类

包含具体的 Agent 实现:
- TeacherAgent: 主协调 Agent,理解用户意图并分发任务
- PainterAgent: 专业绘图 Agent,负责流程图、架构图绘制
"""

from src.agent.agents.teacher import TeacherAgent
from src.agent.agents.painter import PainterAgent

__all__ = [
    "TeacherAgent",
    "PainterAgent",
]
