"""模块名称: canvas_agent
主要功能: SyncCanvas AI Agent - 统一的画布操作 Agent
"""

from typing import Optional, TYPE_CHECKING

from src.agent.base import BaseAgent, AgentConfig
from src.agent.llm import LLMClient
from src.agent.registry import registry
from src.agent.prompts import prompt_manager
from src.logger import get_logger
import src.agent.tools  # noqa: F401  # 确保工具被注册

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


class CanvasAgent(BaseAgent):
    """SyncCanvas AI Agent

    统一的画布操作 Agent，基于 ReAct 循环实现。
    支持绘图、修改、删除等操作。

    通过切换提示词模板实现不同的思考模式:
    - 常规对话: system.jinja2
    - 绘图任务: canvaser.jinja2
    - 控制操作: controller.jinja2
    """

    DEFAULT_CONFIG = AgentConfig(
        max_iterations=15,
        llm_timeout=60.0,
        tool_timeout=30.0,
        total_timeout=300.0,
        enable_room_lock=True,
        enable_self_reflection=True,
        reflection_interval=3,
    )

    def __init__(
        self,
        llm_client: LLMClient,
        run_service: Optional["AgentRunService"] = None,
        config: Optional[AgentConfig] = None,
    ):
        """初始化 CanvasAgent

        Args:
            llm_client: LLM 客户端实例
            run_service: Agent 运行记录服务 (可选)
            config: 自定义配置 (可选)
        """
        system_prompt = self._build_prompt_from_template()

        super().__init__(
            name="CanvasAgent",
            role="SyncCanvas AI Assistant",
            llm_client=llm_client,
            system_prompt=system_prompt,
            config=config or self.DEFAULT_CONFIG,
            run_service=run_service,
        )

        self._register_default_tools()

    def _build_prompt_from_template(self) -> str:
        """从 Jinja2 模板构建系统提示词"""
        try:
            return prompt_manager.render(
                "canvaser.jinja2",
                tools=[
                    {
                        "name": "get_canvas_bounds",
                        "description": "获取画布边界和建议绘图位置",
                    },
                    {"name": "create_flowchart_node", "description": "创建流程图节点"},
                    {"name": "connect_nodes", "description": "用箭头连接两个节点"},
                    {
                        "name": "batch_create_elements",
                        "description": "批量创建元素和连接线",
                    },
                    {"name": "list_elements", "description": "查看画布元素"},
                    {"name": "update_element", "description": "更新元素属性"},
                    {"name": "delete_elements", "description": "删除元素"},
                ],
                layout={
                    "node_width": 160,
                    "node_height": 70,
                    "decision_size": 120,
                    "ellipse_width": 120,
                    "ellipse_height": 50,
                    "vertical_gap": 80,
                    "horizontal_gap": 220,
                    "start_x": 400,
                    "start_y": 50,
                },
                guidelines=[
                    "绘图前务必先调用 get_canvas_bounds",
                    "每次创建节点后记住 element_id",
                    "使用 batch_create_elements 可一次性创建整个图表",
                ],
                enable_cot=True,
            )
        except Exception as e:
            logger.error("Jinja2 模板渲染失败: %s, 使用默认提示词", e)
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """备用提示词"""
        return """你是 SyncCanvas AI 助手，负责在 Excalidraw 画布上绘制图表。

可用工具:
- get_canvas_bounds: 获取画布边界
- create_flowchart_node: 创建节点
- connect_nodes: 连接节点
- batch_create_elements: 批量创建
- list_elements: 查看元素
- update_element: 更新元素
- delete_elements: 删除元素

规则:
1. 先调用 get_canvas_bounds 获取画布状态
2. 记住每个创建的 element_id
3. 保持布局整齐
"""

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        for name, func in registry.get_all_tools().items():
            schema = registry.get_schema(name)
            meta = registry.get_metadata(name)

            if not schema:
                continue

            # 跳过危险工具
            if meta and meta.dangerous:
                continue

            timeout = meta.timeout if meta else 30.0
            retries = meta.retries if meta else 2

            self.register_tool(
                name,
                func,
                schema,
                timeout=timeout,
                retries=retries,
            )

        logger.info("CanvasAgent 已注册 %d 个工具", len(self.tools))
