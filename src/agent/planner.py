"""模块名称: planner
主要功能: Planner Agent - 主要的协调 Agent

负责理解用户意图，管理对话流程，并将绘图任务委托给 Canvaser Agent。
"""

from typing import Optional, TYPE_CHECKING

from src.agent.base import BaseAgent, AgentContext, AgentConfig
from src.agent.llm import LLMClient
from src.agent.registry import registry
from src.agent.prompts import prompt_manager
from src.agent.canvaser import CanvaserAgent
from src.logger import get_logger


if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)

PLANNER_SYSTEM_PROMPT = """你是 SyncCanvas 的 AI 助手，一个多功能的智能白板协作平台助手。

## 核心能力

### 1. 智能对话
- 回答用户问题，提供清晰、专业的解释
- 理解上下文，进行多轮对话
- 帮助用户理解复杂概念

### 2. 白板绘图
- 在画布上绘制流程图、架构图、数据流图
- 管理画布元素（创建、修改、删除）
- 智能布局，避免元素重叠

### 3. 信息获取
- 获取网页内容，提取关键信息
- 分析文本，总结要点
- 获取当前时间，执行数学计算

## 可用工具

### 绘图工具
- `get_canvas_bounds`: 获取画布边界和建议绘图位置 ⚠️ 绘图前必须先调用
- `create_flowchart_node`: 创建流程图节点 (矩形/菱形/椭圆 + 文字)
- `connect_nodes`: 用箭头连接两个节点
- `create_element`: 创建基础图形
- `list_elements`: 查看画布元素
- `update_element`: 更新元素属性
- `delete_elements`: 删除元素
- `clear_canvas`: 清空画布

### 信息工具
- `fetch_webpage`: 获取网页内容
- `get_current_time`: 获取当前时间
- `calculate`: 执行数学计算

## 工作流程

### 普通对话
直接回答用户问题，提供有帮助的信息。

### 绘图任务
1. 首先调用 `get_canvas_bounds` 获取画布状态
2. 根据 `suggested_start` 规划元素位置
3. 依次创建节点，记录返回的 element_id
4. 使用 connect_nodes 连接节点
5. 确认完成

### 信息查询
1. 使用 `fetch_webpage` 获取网页内容
2. 分析并总结关键信息
3. 如需可视化，在白板上绘制

## 注意事项
1. 绘图前务必先获取画布边界，避免覆盖现有内容
2. 每次创建节点后记住 element_id，用于后续连接
3. 保持回复简洁友好
4. 遇到复杂绘图任务，会自动委托给专业绘图助手

你是用户的得力助手，随时准备帮助他们完成工作！
"""


class PlannerAgent(BaseAgent):
    """Planner Agent - 主协调者

    负责理解用户意图并协调任务执行。
    可以直接执行简单任务或委托复杂绘图任务给 CanvaserAgent。

    Attributes:
        canvaser: Canvaser Agent 实例
        router: LLM 路由器
        run_service: Agent 运行记录服务
    """

    # Planner 专用配置
    PLANNER_CONFIG = AgentConfig(
        max_iterations=15,
        llm_timeout=60.0,
        tool_timeout=30.0,
        total_timeout=300.0,
        enable_room_lock=True,
    )

    def __init__(
        self,
        llm_client: LLMClient,
        run_service: Optional["AgentRunService"] = None,
        config: Optional[AgentConfig] = None,
    ):
        """初始化 Planner Agent

        Args:
            llm_client: LLM 客户端实例
            run_service: Agent 运行记录服务 (可选)
            config: 自定义配置 (可选)
        """
        # 初始化路由器
        from src.agent.pipeline.router import get_router

        self.router = get_router()

        # 构建系统提示词
        system_prompt = self._build_prompt_from_template()

        super().__init__(
            name="Planner",
            role="Orchestrator",
            llm_client=llm_client,
            system_prompt=system_prompt,
            config=config or self.PLANNER_CONFIG,
            run_service=run_service,
        )
        # 初始化 Canvaser Agent
        self.canvaser = CanvaserAgent(llm_client, run_service)
        self._register_default_tools()

    def _build_prompt_from_template(self) -> str:
        """从 Jinja2 模板构建系统提示词

        Returns:
            str: 渲染后的系统提示词
        """
        try:
            return prompt_manager.render(
                "planner.jinja2",
                drawing_tools=[
                    {
                        "name": "get_canvas_bounds",
                        "description": "获取画布边界和建议绘图位置",
                    },
                    {"name": "create_flowchart_node", "description": "创建流程图节点"},
                    {"name": "connect_nodes", "description": "用箭头连接两个节点"},
                    {"name": "create_element", "description": "创建基础图形"},
                    {"name": "list_elements", "description": "查看画布元素"},
                    {"name": "update_element", "description": "更新元素属性"},
                    {"name": "delete_elements", "description": "删除元素"},
                    {"name": "clear_canvas", "description": "清空画布"},
                ],
                info_tools=[
                    {"name": "fetch_webpage", "description": "获取网页内容"},
                    {"name": "get_current_time", "description": "获取当前时间"},
                    {"name": "calculate", "description": "执行数学计算"},
                ],
                guidelines=[
                    "绘图前务必先获取画布边界，避免覆盖现有内容",
                    "每次创建节点后记住 element_id，用于后续连接",
                    "保持回复简洁友好",
                    "遇到复杂绘图任务，会自动委托给专业绘图助手",
                ],
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Jinja2 模板渲染失败，使用静态 prompt: %s", e)
            return PLANNER_SYSTEM_PROMPT

    def _register_default_tools(self) -> None:
        """注册默认工具

        注册所有非危险工具。
        """
        for name, func in registry.get_all_tools().items():
            schema = registry.get_schema(name)
            meta = registry.get_metadata(name)

            if not schema:
                continue

            # 跳过危险工具
            if meta and meta.dangerous:
                continue

            # 获取工具配置
            timeout = meta.timeout if meta else 30.0
            retries = meta.retries if meta else 2

            self.register_tool(
                name,
                func,
                schema,
                timeout=timeout,
                retries=retries,
            )

        logger.info("Planner Agent 已注册 %s 个工具", len(self.tools))

    async def run(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float = 0.3,
    ) -> str:
        """执行任务

        使用 Router 智能分类任务，根据 TaskIntent 分发:
        - GENERATE: 委托给 CanvaserAgent (已集成 Pipeline)
        - MODIFY/DELETE/LAYOUT: 使用 Pipeline CONTROL 模式
        - QUERY/其他: 使用 ReAct 循环

        Args:
            context: Agent 上下文
            user_input: 用户输入
            temperature: LLM 温度参数

        Returns:
            str: 执行结果
        """
        from src.agent.pipeline import create_pipeline
        from src.agent.pipeline.cognition import get_cognition
        from src.agent.pipeline.router import TaskIntent
        from src.agent.pipeline.reasoning import ReasoningMode

        # Phase 1: 获取画布状态
        cognition = get_cognition()
        canvas_state = await cognition.hydrate(context)

        # Phase 2: 使用 Router 分类任务
        task, _ = self.router.classify_and_select(user_input, canvas_state)

        logger.info(
            "任务分类: intent=%s, tier=%s, complexity=%.2f",
            task.intent.value,
            task.tier.value,
            task.complexity,
            extra={"run_id": context.run_id},
        )

        # 根据 Intent 分发任务
        if task.intent == TaskIntent.GENERATE:
            # 创建任务 -> 委托给 Canvaser (已集成 Pipeline)
            await self._log_action(
                context,
                "delegate",
                {"target": "canvaser", "intent": task.intent.value},
                {"status": "delegated"},
            )
            return await self.canvaser.run(context, user_input, temperature=0.2)

        elif task.intent in (TaskIntent.MODIFY, TaskIntent.DELETE, TaskIntent.LAYOUT):
            # 控制任务 -> 使用 Pipeline CONTROL 模式
            pipeline = create_pipeline(self.llm)
            result = await pipeline.execute(
                context, user_input, temperature, mode=ReasoningMode.CONTROL
            )
            if result.success:
                return result.message
            else:
                return f"执行失败: {result.message}"

        else:
            # 对话/查询 -> 使用 ReAct 循环
            return await super().run(context, user_input, temperature)
