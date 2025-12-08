"""模块名称: teacher
主要功能: Teacher Agent - 主要的协调 Agent

负责理解用户意图，管理对话流程，并将绘图任务委托给 Painter Agent。
"""

from typing import Optional, TYPE_CHECKING

from src.ai_engine.core.agent import BaseAgent, AgentContext
from src.ai_engine.core.llm import LLMClient
from src.ai_engine.core.tools import registry
from src.ai_engine.agents.painter import PainterAgent
from src.logger import get_logger

# 导入工具以确保它们被注册
import src.ai_engine.tools.excalidraw_tools  # noqa: F401
import src.ai_engine.tools.knowledge_tools  # noqa: F401

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)

TEACHER_SYSTEM_PROMPT = """你是一个专业的 AI 白板助手。
你的目标是帮助用户通过清晰的解释和可视化来学习和理解概念。

## 核心能力
1. 回答用户问题，提供清晰的解释
2. 在白板上绘制图表来辅助说明
3. 管理画布元素（创建、修改、删除）

## 可用工具
- create_flowchart_node: 创建流程图节点
- connect_nodes: 连接两个节点
- create_element: 创建基础图形元素
- list_elements: 列出画布元素
- update_element: 更新元素属性
- delete_elements: 删除指定元素
- clear_canvas: 清空画布

## 工作流程
1. 理解用户的请求
2. 如果是绘图请求，规划需要的元素和布局
3. 使用工具逐步执行
4. 确认完成并给出反馈

## 绘图指南
当需要绘制流程图时:
- 使用 ellipse 表示开始/结束
- 使用 rectangle 表示处理步骤
- 使用 diamond 表示判断/条件
- 从上到下布局，Y 坐标递增

你是协调者，可以直接使用工具或将复杂绘图任务委托给专门的绘图助手。
"""


class TeacherAgent(BaseAgent):
    """Teacher Agent - 主协调者

    负责理解用户意图并协调任务执行。
    可以直接执行简单任务或委托复杂绘图任务给 PainterAgent。

    Attributes:
        painter: Painter Agent 实例
        run_service: Agent 运行记录服务
    """

    # 绘图相关关键词
    DRAW_KEYWORDS = [
        "draw", "diagram", "flowchart", "sketch", "layout", "uml", "erd",
        "graph", "visualize", "paint", "illustrate", "chart",
        "画", "绘制", "绘图", "流程图", "数据流图", "架构图", "示意图",
        "思维导图", "关系图", "时序图", "类图"
    ]

    def __init__(
        self,
        llm_client: LLMClient,
        run_service: Optional["AgentRunService"] = None
    ):
        """初始化 Teacher Agent

        Args:
            llm_client: LLM 客户端实例
            run_service: Agent 运行记录服务 (可选)
        """
        super().__init__(
            name="Teacher",
            role="Orchestrator",
            llm_client=llm_client,
            system_prompt=TEACHER_SYSTEM_PROMPT,
            max_iterations=15,
            run_service=run_service,
        )
        # 初始化 Painter Agent
        self.painter = PainterAgent(llm_client, run_service)
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        # 从全局注册表加载所有工具
        for name, func in registry.get_all_tools().items():
            schema = registry._schemas.get(name)
            if schema:
                self.register_tool(name, func, schema)

        logger.info(f"Teacher Agent 已注册 {len(self.tools)} 个工具")

    def _should_delegate_to_painter(self, text: str) -> bool:
        """判断是否应该委托给 Painter Agent

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否应该委托
        """
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.DRAW_KEYWORDS)

    async def run(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float = 0.3,
    ) -> str:
        """执行任务

        根据用户输入判断是否委托给 Painter Agent。

        Args:
            context: Agent 上下文
            user_input: 用户输入
            temperature: LLM 温度参数

        Returns:
            str: 执行结果
        """
        # 如果是绘图相关请求，委托给 Painter
        if self._should_delegate_to_painter(user_input):
            logger.info("检测到绘图请求，委托给 Painter Agent", extra={
                "run_id": context.run_id,
                "session_id": context.session_id
            })

            # 记录委托行为
            await self._log_action(
                context,
                "delegate",
                {"target": "painter", "reason": "drawing_request"},
                {"status": "delegated"}
            )

            return await self.painter.run(context, user_input, temperature=0.2)

        # 否则自己处理
        return await super().run(context, user_input, temperature)
