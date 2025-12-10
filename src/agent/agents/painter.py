"""模块名称: painter
主要功能: Painter Agent - 专业的图形绘制 Agent

负责将用户的绘图需求转换为 Excalidraw 元素操作。
支持流程图、数据流图、架构图等多种图表类型。
使用 ReAct 架构进行推理和执行。
"""

from dataclasses import dataclass, asdict
import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.agent.core.agent import PlanningAgent, AgentContext, AgentConfig
from src.agent.core.llm import LLMClient
from src.agent.core.tools import registry, ToolCategory
from src.agent.prompts import prompt_manager
from src.logger import get_logger

# 确保工具被加载
import src.agent.tools  # noqa: F401

if TYPE_CHECKING:
    from src.services.agent_runs import AgentRunService

logger = get_logger(__name__)


# ==================== 布局常量 ====================


@dataclass
class LayoutConfig:
    """流程图布局配置"""

    node_width: int = 160
    node_height: int = 70
    decision_size: int = 120
    ellipse_width: int = 120
    ellipse_height: int = 50
    vertical_gap: int = 80
    horizontal_gap: int = 220
    start_x: int = 400
    start_y: int = 50

    def to_dict(self) -> Dict[str, int]:
        """转换为字典 (用于 Jinja2 模板)"""
        return asdict(self)


# ==================== 系统提示词 ====================

PAINTER_SYSTEM_PROMPT = """你是一个专业的图形绘制助手 (Painter Agent)，专门负责在 Excalidraw 白板上绘制流程图、数据流图、架构图等技术图表。

## 核心职责
根据用户描述，准确绘制技术图表。你需要:
1. 理解用户需求，规划图表结构
2. 计算合理的节点位置
3. 依次创建节点并连接

## 图形标准

### 流程图节点类型
- **ellipse (椭圆)**: 开始/结束节点，尺寸 120x50
- **rectangle (矩形)**: 处理/操作步骤，尺寸 160x70
- **diamond (菱形)**: 判断/条件分支，尺寸 120x120

### 布局规则
- 起始位置: X=400 (水平居中), Y=50 (顶部留白)
- 垂直间距: 节点间隔 80px
- 水平分支: 左右偏移 ±220px

### 坐标计算公式
```
节点N的Y坐标 = START_Y + Σ(前面节点高度) + (N-1) * VERTICAL_GAP

示例 (标准流程图):
- 开始 (ellipse):    Y = 50
- 步骤1 (rectangle): Y = 50 + 50 + 80 = 180
- 判断 (diamond):    Y = 180 + 70 + 80 = 330
- 步骤2 (rectangle): Y = 330 + 120 + 80 = 530
- 结束 (ellipse):    Y = 530 + 70 + 80 = 680
```

### 分支布局
当遇到判断节点时:
- Yes/是 分支: X = 400 + 220 = 620
- No/否 分支: X = 400 - 220 = 180
- 分支后汇合: 回到 X = 400

## 执行流程

### 步骤 0: 获取画布状态 ⚠️ 重要
**首先**调用 `get_canvas_bounds` 获取当前画布状态:
- 如果画布为空，使用 suggested_start 作为起始位置
- 如果有现有元素，在 suggested_start 位置绘制新内容，避免覆盖
- 这一步必须先执行！

### 步骤 1: 分析需求
仔细阅读用户描述，识别:
- 需要哪些节点 (开始、步骤、判断、结束)
- 节点之间的连接关系
- 是否有分支和汇合

### 步骤 2: 规划布局
基于 get_canvas_bounds 返回的 suggested_start，为每个节点计算坐标:
- 从 suggested_start.x, suggested_start.y 开始
- 每个节点高度 + 80px 间距
- 分支时水平偏移

### 步骤 3: 创建节点
使用 `create_flowchart_node` 依次创建节点:
- 记住每个节点返回的 `element_id`
- 这些 ID 用于后续连接

### 步骤 4: 连接节点
使用 `connect_nodes` 创建箭头:
- 使用之前记录的 element_id
- 判断分支要加标签 (如 "是"/"否")

## 可用工具

### create_flowchart_node
创建流程图节点 (形状+绑定文本)
参数:
- label: 节点文字
- node_type: rectangle/diamond/ellipse
- x, y: 坐标
- width, height: 尺寸

### connect_nodes
用箭头连接两个节点
参数:
- from_id: 起始节点 ID
- to_id: 目标节点 ID
- label: 连线标签 (可选)

### list_elements
查看画布现有元素

### delete_elements
删除指定元素

### clear_canvas
清空画布

## 注意事项
1. 每次创建节点后，务必记住返回的 element_id
2. 连接时使用正确的 from_id 和 to_id
3. 判断分支必须添加 label (如 "是"/"否")
4. 保持图表简洁，布局整齐

## 示例

用户: "画一个登录流程图"

分析:
- 开始 → 输入账号密码 → 验证 → (成功?)是→登录成功/否→显示错误 → 结束

执行:
1. create_flowchart_node(label="开始", node_type="ellipse", x=400, y=50)  → 记录 id1
2. create_flowchart_node(label="输入账号密码", node_type="rectangle", x=400, y=180)  → 记录 id2
3. create_flowchart_node(label="验证", node_type="diamond", x=400, y=330)  → 记录 id3
4. create_flowchart_node(label="登录成功", node_type="rectangle", x=620, y=530)  → 记录 id4
5. create_flowchart_node(label="显示错误", node_type="rectangle", x=180, y=530)  → 记录 id5
6. create_flowchart_node(label="结束", node_type="ellipse", x=400, y=680)  → 记录 id6
7. connect_nodes(from_id=id1, to_id=id2)
8. connect_nodes(from_id=id2, to_id=id3)
9. connect_nodes(from_id=id3, to_id=id4, label="是")
10. connect_nodes(from_id=id3, to_id=id5, label="否")
11. connect_nodes(from_id=id4, to_id=id6)
12. connect_nodes(from_id=id5, to_id=id6)

现在请根据用户需求绘制图表。先分析，再计算坐标，最后逐步执行!
"""


class PainterAgent(PlanningAgent):
    """Painter Agent - 专业图形绘制

    专门用于绘制流程图、数据流图、架构图等技术图表。
    继承自 PlanningAgent，具备任务规划能力。
    使用 Jinja2 模板构建系统提示词。

    Attributes:
        layout_config: 布局配置
        node_registry: 已创建节点的 ID 映射
    """

    # Painter 专用配置
    PAINTER_CONFIG = AgentConfig(
        max_iterations=25,  # 绘图需要更多迭代
        llm_timeout=90.0,  # LLM 调用超时
        tool_timeout=30.0,  # 工具执行超时
        total_timeout=600.0,  # 总超时 10 分钟
        enable_room_lock=True,  # 启用房间锁
    )

    def __init__(
        self,
        llm_client: LLMClient,
        run_service: Optional["AgentRunService"] = None,
        config: Optional[AgentConfig] = None,
    ):
        """初始化 Painter Agent

        Args:
            llm_client: LLM 客户端实例
            run_service: Agent 运行记录服务 (可选)
            config: 自定义配置 (可选)
        """
        self.layout_config = LayoutConfig()

        # 尝试使用 Jinja2 模板，失败则使用静态 prompt
        system_prompt = self._build_prompt_from_template()

        super().__init__(
            name="Painter",
            role="图形绘制专家",
            llm_client=llm_client,
            system_prompt=system_prompt,
            config=config or self.PAINTER_CONFIG,
            run_service=run_service,
            enable_planning=True,
        )
        self.node_registry: Dict[str, str] = {}  # 逻辑名称 -> element_id
        self._register_tools()

    def _build_prompt_from_template(self) -> str:
        """从 Jinja2 模板构建系统提示词

        Returns:
            str: 渲染后的系统提示词
        """
        try:
            return prompt_manager.render(
                "painter.jinja2",
                layout=self.layout_config.to_dict(),
                tools=[
                    {
                        "name": "get_canvas_bounds",
                        "description": "获取画布边界和建议绘图位置",
                        "params": [],
                    },
                    {
                        "name": "create_flowchart_node",
                        "description": "创建流程图节点 (形状+绑定文本)",
                        "params": [
                            {"name": "label", "desc": "节点文字"},
                            {"name": "node_type", "desc": "rectangle/diamond/ellipse"},
                            {"name": "x, y", "desc": "坐标"},
                        ],
                    },
                    {
                        "name": "connect_nodes",
                        "description": "用箭头连接两个节点",
                        "params": [
                            {"name": "from_id", "desc": "起始节点 ID"},
                            {"name": "to_id", "desc": "目标节点 ID"},
                            {"name": "label", "desc": "连线标签 (可选)"},
                        ],
                    },
                    {
                        "name": "list_elements",
                        "description": "查看画布现有元素",
                        "params": [],
                    },
                    {
                        "name": "delete_elements",
                        "description": "删除指定元素",
                        "params": [],
                    },
                    {"name": "clear_canvas", "description": "清空画布", "params": []},
                ],
                guidelines=[
                    "每次创建节点后，务必记住返回的 element_id",
                    "连接时使用正确的 from_id 和 to_id",
                    '判断分支必须添加 label (如 "是"/"否")',
                    "保持图表简洁，布局整齐",
                ],
                examples=[
                    {
                        "title": "登录流程图",
                        "user_input": "画一个登录流程图",
                        "analysis": "开始 → 输入账号密码 → 验证 → (成功?)是→登录成功/否→显示错误 → 结束",
                        "steps": [
                            'create_flowchart_node(label="开始", node_type="ellipse", x=400, y=50) → 记录 id1',
                            'create_flowchart_node(label="输入账号密码", node_type="rectangle", x=400, y=180) → 记录 id2',
                            'create_flowchart_node(label="验证", node_type="diamond", x=400, y=330) → 记录 id3',
                            "connect_nodes(from_id=id1, to_id=id2)",
                            "connect_nodes(from_id=id2, to_id=id3)",
                            "...",
                        ],
                    }
                ],
            )
        except Exception as e:
            logger.warning(f"Jinja2 模板渲染失败，使用静态 prompt: {e}")
            return PAINTER_SYSTEM_PROMPT

    def _register_tools(self) -> None:
        """注册绘图相关工具

        只注册画布相关和通用工具，不注册危险操作。
        """
        # 从全局注册表加载工具
        for name, func in registry.get_all_tools().items():
            schema = registry._schemas.get(name)
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

        logger.info(f"Painter Agent 已注册 {len(self.tools)} 个工具")

    def _build_system_prompt(self) -> str:
        """构建系统提示词

        包含布局配置信息，帮助 LLM 更好地计算坐标。
        """
        base_prompt = super()._build_system_prompt()

        # 添加当前布局配置
        config_info = f"""
## 当前布局配置
- 矩形节点: {self.layout_config.node_width}x{self.layout_config.node_height}
- 菱形节点: {self.layout_config.decision_size}x{self.layout_config.decision_size}
- 椭圆节点: {self.layout_config.ellipse_width}x{self.layout_config.ellipse_height}
- 垂直间距: {self.layout_config.vertical_gap}px
- 水平分支间距: {self.layout_config.horizontal_gap}px
- 起始坐标: ({self.layout_config.start_x}, {self.layout_config.start_y})
"""
        return base_prompt + config_info

    async def run(
        self,
        context: AgentContext,
        user_input: str,
        temperature: float = 0.2,  # 使用较低温度提高一致性
    ) -> str:
        """执行绘图任务

        Args:
            context: Agent 上下文
            user_input: 用户输入
            temperature: LLM 温度参数

        Returns:
            str: 执行结果描述
        """
        # 重置节点注册表
        self.node_registry = {}

        # 执行 ReAct 循环
        result = await super().run(context, user_input, temperature)

        # 生成执行摘要
        summary = self._generate_summary(context)

        return f"{result}\n\n{summary}" if summary else result

    def _generate_summary(self, context: AgentContext) -> str:
        """生成执行摘要

        Args:
            context: Agent 上下文

        Returns:
            str: 执行摘要
        """
        if not context.tool_results:
            return ""

        node_count = 0
        connection_count = 0
        element_ids = []

        for result in context.tool_results:
            tool = result.get("tool", "")
            result_str = result.get("result", "{}")

            try:
                result_data = (
                    json.loads(result_str)
                    if isinstance(result_str, str)
                    else result_str
                )
            except (json.JSONDecodeError, TypeError):
                result_data = {}

            if tool in ["create_flowchart_node", "create_element"]:
                node_count += 1
                if result_data.get("element_id"):
                    element_ids.append(result_data["element_id"])
            elif tool == "connect_nodes":
                connection_count += 1

        if node_count > 0 or connection_count > 0:
            summary = (
                f"[绘制完成] 创建了 {node_count} 个节点，{connection_count} 条连接线。"
            )
            if element_ids:
                summary += f"\n创建的元素 ID: {', '.join(element_ids[:5])}"
                if len(element_ids) > 5:
                    summary += f"... 等共 {len(element_ids)} 个"
            return summary

        return ""


# ==================== 布局辅助类 ====================


class FlowchartLayout:
    """流程图布局计算器

    提供静态方法用于计算节点位置。

    Attributes:
        无实例属性，全部为静态方法
    """

    @staticmethod
    def calculate_node_position(
        node_index: int,
        node_type: str,
        previous_nodes: List[Dict[str, Any]],
        branch_direction: Optional[str] = None,
    ) -> Dict[str, float]:
        """计算节点位置

        Args:
            node_index: 节点索引 (从0开始)
            node_type: 节点类型 (rectangle/diamond/ellipse)
            previous_nodes: 之前的节点列表，包含 {type, height} 信息
            branch_direction: 分支方向 (left/right/None)

        Returns:
            dict: 包含 x, y, width, height 的位置信息
        """
        config = LayoutConfig()

        # 确定节点尺寸
        if node_type == "diamond":
            width = config.DECISION_SIZE
            height = config.DECISION_SIZE
        elif node_type == "ellipse":
            width = config.ELLIPSE_WIDTH
            height = config.ELLIPSE_HEIGHT
        else:  # rectangle
            width = config.NODE_WIDTH
            height = config.NODE_HEIGHT

        # 计算 Y 坐标
        y = config.START_Y
        for prev_node in previous_nodes:
            y += prev_node.get("height", config.NODE_HEIGHT) + config.VERTICAL_GAP

        # 计算 X 坐标
        x = config.START_X
        if branch_direction == "left":
            x -= config.HORIZONTAL_GAP
        elif branch_direction == "right":
            x += config.HORIZONTAL_GAP

        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }

    @staticmethod
    def generate_flowchart_plan(
        steps: List[str],
        has_decision: bool = False,
        decision_index: int = -1,
    ) -> List[Dict[str, Any]]:
        """生成流程图布局计划

        Args:
            steps: 步骤描述列表
            has_decision: 是否包含判断节点
            decision_index: 判断节点在列表中的索引

        Returns:
            list: 节点布局计划列表
        """
        config = LayoutConfig()
        plan = []
        current_y = config.START_Y

        for i, step in enumerate(steps):
            # 确定节点类型
            if i == 0:
                node_type = "ellipse"  # 开始
                width = config.ELLIPSE_WIDTH
                height = config.ELLIPSE_HEIGHT
            elif i == len(steps) - 1:
                node_type = "ellipse"  # 结束
                width = config.ELLIPSE_WIDTH
                height = config.ELLIPSE_HEIGHT
            elif has_decision and i == decision_index:
                node_type = "diamond"  # 判断
                width = config.DECISION_SIZE
                height = config.DECISION_SIZE
            else:
                node_type = "rectangle"  # 普通步骤
                width = config.NODE_WIDTH
                height = config.NODE_HEIGHT

            plan.append(
                {
                    "label": step,
                    "node_type": node_type,
                    "x": config.START_X,
                    "y": current_y,
                    "width": width,
                    "height": height,
                }
            )

            current_y += height + config.VERTICAL_GAP

        return plan
