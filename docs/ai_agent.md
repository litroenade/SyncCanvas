# AI Agent 架构设计文档

## 概述

SyncCanvas 的 AI Agent 系统采用 **ReAct (Reasoning + Acting)** 架构，实现了一个能够理解用户自然语言描述并在白板上绘制技术图表的智能助手。

## 架构图

```
用户请求
    │
    ▼
┌─────────────────┐
│   AI Router     │  ← HTTP API 入口
│  /ai/generate   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AIService     │  ← 服务层，管理 Agent 生命周期
└────────┬────────┘
         │
         ▼
┌─────────────────┐     委托绘图请求     ┌─────────────────┐
│  TeacherAgent   │ ──────────────────► │  PainterAgent   │
│   (协调者)       │                     │  (绘图专家)      │
└────────┬────────┘                     └────────┬────────┘
         │                                       │
         │           ┌───────────────────────────┘
         │           │
         ▼           ▼
┌─────────────────────────┐
│      Tool Registry      │  ← 工具注册中心
├─────────────────────────┤
│ - create_flowchart_node │
│ - connect_nodes         │
│ - list_elements         │
│ - update_element        │
│ - delete_elements       │
│ - clear_canvas          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   WebSocket Server      │  ← 直接操作 CRDT 文档
│   (Yjs Document)        │
└─────────────────────────┘
```

## 核心组件

### 1. BaseAgent (`src/ai_engine/core/agent.py`)

ReAct Agent 的抽象基类，实现标准的 Think → Act → Observe 循环。

#### 关键属性

```python
class BaseAgent(ABC):
    DEFAULT_MAX_ITERATIONS: int = 15  # 最大迭代次数
    DEFAULT_TEMPERATURE: float = 0.3  # LLM 温度参数
    
    def __init__(self, ...):
        self.name = name              # Agent 名称
        self.role = role              # Agent 角色
        self.llm = llm_client         # LLM 客户端
        self.system_prompt = ...      # 系统提示词
        self.tools = {}               # 已注册工具字典
        self.run_service = ...        # 运行记录服务
```

#### ReAct 循环核心逻辑

```python
async def run(self, context, user_input, temperature):
    messages = [
        {"role": "system", "content": self._build_system_prompt()},
        {"role": "user", "content": user_input}
    ]
    
    while iteration < self.max_iterations:
        # ========== THINK: LLM 推理 ==========
        response = await self.llm.chat_completion(
            messages=messages,
            tools=tool_definitions,
            tool_choice="auto"
        )
        
        # ========== ACT: 执行工具 ==========
        if response.tool_calls:
            for tool_call in response.tool_calls:
                result = await self._execute_tool(...)
                
                # ========== OBSERVE: 记录结果 ==========
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str
                })
            continue  # 继续循环
        
        # 无工具调用，任务完成
        return response.content
```

#### AgentContext 上下文

```python
@dataclass
class AgentContext:
    run_id: int                    # 运行记录 ID
    session_id: str                # 房间 ID
    user_id: Optional[str]         # 用户 ID
    shared_state: Dict[str, Any]   # 共享状态
    tool_results: List[Dict]       # 工具调用历史
    created_element_ids: List[str] # 创建的元素 ID
```

### 2. PlanningAgent

继承自 BaseAgent，增加任务规划能力。

```python
class PlanningAgent(BaseAgent):
    PLANNING_PROMPT_TEMPLATE = """
    ## 执行策略
    1. 分析需求: 理解用户想要什么
    2. 规划步骤: 列出需要创建的元素和连接
    3. 计算坐标: 确定每个元素的位置
    4. 逐步执行: 按照规划依次创建元素
    """
```

### 3. TeacherAgent (`src/ai_engine/agents/teacher.py`)

主协调者，负责理解用户意图并路由请求。

#### 委托判断逻辑

```python
DRAW_KEYWORDS = [
    "draw", "diagram", "flowchart", "uml", "graph",
    "画", "绘制", "流程图", "数据流图", "架构图"
]

def _should_delegate_to_painter(self, text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in self.DRAW_KEYWORDS)

async def run(self, context, user_input, temperature):
    if self._should_delegate_to_painter(user_input):
        # 委托给 PainterAgent
        return await self.painter.run(context, user_input, temperature=0.2)
    # 否则自己处理
    return await super().run(context, user_input, temperature)
```

### 4. PainterAgent (`src/ai_engine/agents/painter.py`)

专业的图形绘制 Agent，负责流程图、数据流图等技术图表的绘制。

#### 布局配置

```python
class LayoutConfig:
    NODE_WIDTH: int = 160          # 矩形节点宽度
    NODE_HEIGHT: int = 70          # 矩形节点高度
    DECISION_SIZE: int = 120       # 菱形节点尺寸
    ELLIPSE_WIDTH: int = 120       # 椭圆节点宽度
    ELLIPSE_HEIGHT: int = 50       # 椭圆节点高度
    VERTICAL_GAP: int = 80         # 垂直间距
    HORIZONTAL_GAP: int = 220      # 水平分支间距
    START_X: int = 400             # 起始 X 坐标
    START_Y: int = 50              # 起始 Y 坐标
```

#### 流程图坐标计算公式

```
节点N的Y坐标 = START_Y + Σ(前面节点高度) + (N-1) * VERTICAL_GAP

示例 (标准流程图):
- 开始 (ellipse):    Y = 50
- 步骤1 (rectangle): Y = 50 + 50 + 80 = 180
- 判断 (diamond):    Y = 180 + 70 + 80 = 330
- 步骤2 (rectangle): Y = 330 + 120 + 80 = 530
- 结束 (ellipse):    Y = 530 + 70 + 80 = 680

分支布局:
- Yes/是 分支: X = START_X + HORIZONTAL_GAP = 620
- No/否 分支: X = START_X - HORIZONTAL_GAP = 180
```

#### 系统提示词核心内容

```
## 图形标准
- ellipse (椭圆): 开始/结束节点
- rectangle (矩形): 处理/操作步骤  
- diamond (菱形): 判断/条件分支

## 执行流程
1. 分析需求 → 识别节点和连接关系
2. 规划布局 → 计算每个节点坐标
3. 创建节点 → 使用 create_flowchart_node，记住 element_id
4. 连接节点 → 使用 connect_nodes，添加分支标签
```

## 工具系统

### ToolRegistry (`src/ai_engine/core/tools.py`)

全局工具注册中心，使用装饰器模式注册工具。

```python
registry = ToolRegistry()

@registry.register("tool_name", "工具描述", ArgsSchema)
async def tool_function(arg1, arg2, context=None):
    # 实现逻辑
    return {"status": "success", ...}
```

### Excalidraw 工具 (`src/ai_engine/tools/excalidraw_tools.py`)

| 工具名称 | 功能 | 关键参数 |
|---------|------|---------|
| `create_flowchart_node` | 创建流程图节点 | label, node_type, x, y, width, height |
| `connect_nodes` | 连接两个节点 | from_id, to_id, label |
| `create_element` | 创建基础图形 | element_type, x, y, width, height |
| `list_elements` | 列出画布元素 | limit |
| `get_element` | 获取元素详情 | element_id |
| `update_element` | 更新元素属性 | element_id, x, y, width, height, text |
| `delete_elements` | 删除元素 | element_ids |
| `clear_canvas` | 清空画布 | confirm |

#### create_flowchart_node 实现

```python
async def create_flowchart_node(
    label: str,
    node_type: str = "rectangle",
    x: float = 400,
    y: float = 50,
    width: float = 160,
    height: float = 70,
    context: AgentContext = None,
):
    room_id = context.session_id
    room = await websocket_server.get_room(room_id)
    doc = room.ydoc
    elements_array = doc.get("elements", type=Array)

    # 1. 创建形状元素
    shape = _base_excalidraw_element(node_type, x, y, width, height)
    shape_id = shape["id"]
    
    # 2. 创建绑定的文本元素
    text_element = {
        "id": text_id,
        "type": "text",
        "text": label,
        "containerId": shape_id,  # 绑定到形状
        ...
    }
    
    # 3. 更新形状的 boundElements
    shape["boundElements"] = [{"id": text_id, "type": "text"}]
    
    # 4. 写入 CRDT 文档
    with doc.transaction(origin="ai-engine/create_flowchart_node"):
        elements_array.append(_element_to_ymap(shape))
        elements_array.append(_element_to_ymap(text_element))
    
    return {
        "status": "success",
        "element_id": shape_id,  # 返回 ID 用于后续连接
        "text_id": text_id,
    }
```

#### connect_nodes 实现

```python
async def connect_nodes(
    from_id: str,
    to_id: str,
    label: Optional[str] = None,
    context: AgentContext = None,
):
    # 1. 查找起始和结束节点
    _, start_node = _find_element_by_id(elements_array, from_id)
    _, end_node = _find_element_by_id(elements_array, to_id)
    
    # 2. 计算连接点 (智能判断从哪个边连接)
    if end_cy > start_cy:  # 目标在下方
        arrow_start_y = start_y + start_h  # 从底边出发
        arrow_end_y = end_y                # 到顶边
    
    # 3. 创建箭头元素
    arrow = {
        "type": "arrow",
        "points": [[0, 0], [end_x - start_x, end_y - start_y]],
        "startBinding": {"elementId": from_id, ...},
        "endBinding": {"elementId": to_id, ...},
        "endArrowhead": "arrow",
    }
    
    # 4. 如果有标签，创建标签文本
    if label:
        label_element = {...}
    
    return {"status": "success", "arrow_id": arrow_id}
```

## 服务层

### AIService (`src/services/ai_service.py`)

高级服务接口，管理 Agent 生命周期。

```python
class AIService:
    async def process_request(self, user_input, session_id, db, user_id=None):
        # 1. 创建运行记录
        run = run_service.create_run(room_id=session_id, prompt=user_input)
        
        # 2. 初始化上下文
        context = AgentContext(run_id=run.id, session_id=session_id)
        
        # 3. 初始化并执行 Agent
        teacher = TeacherAgent(self.llm_client, run_service)
        response = await teacher.run(context, user_input)
        
        # 4. 更新运行状态
        run_service.complete_run(run.id, message=response)
        
        return {
            "status": "success",
            "response": response,
            "run_id": run.id,
            "elements_created": context.created_element_ids,
        }
```

### AgentRunService (`src/services/agent_runs.py`)

Agent 运行生命周期管理。

```python
class AgentRunService:
    def create_run(self, room_id, prompt, model) -> AgentRun
    def log_action(self, run_id, tool, arguments, result) -> AgentAction
    def complete_run(self, run_id, message) -> AgentRun
    def fail_run(self, run_id, error) -> AgentRun
    def get_run_detail(self, run_id) -> Dict
```

## 数据模型

### AgentRun

```python
class AgentRun(SQLModel, table=True):
    id: int
    room_id: str           # 房间 ID
    prompt: str            # 用户输入
    model: str             # 使用的模型
    status: str            # running/completed/failed
    message: str           # 响应消息
    created_at: int        # 创建时间
    finished_at: int       # 完成时间
```

### AgentAction

```python
class AgentAction(SQLModel, table=True):
    id: int
    run_id: int            # 关联的运行 ID
    tool: str              # 工具名称
    arguments: dict        # 调用参数 (JSON)
    result: dict           # 执行结果 (JSON)
    created_at: int        # 创建时间
```

## API 接口

### POST /ai/generate

请求生成/绘图。

**请求体:**
```json
{
    "prompt": "画一个用户登录的流程图",
    "room_id": "abc-123"
}
```

**响应:**
```json
{
    "status": "success",
    "response": "已完成流程图绘制...",
    "run_id": 42,
    "elements_created": ["rectangle_a1b2c3d4", "diamond_e5f6g7h8"],
    "tools_used": ["create_flowchart_node", "connect_nodes"]
}
```

### GET /ai/runs/{room_id}

获取房间的 AI 运行历史。

### GET /ai/run/{run_id}

获取运行详情，包含所有工具调用记录。

## 使用示例

### 绘制登录流程图

**用户输入:** `画一个用户登录的流程图，包含输入账号密码、验证、成功或失败的分支`

**Agent 执行过程:**

1. TeacherAgent 检测到绘图关键词，委托给 PainterAgent

2. PainterAgent 分析需求，规划节点:
   - 开始 (ellipse)
   - 输入账号密码 (rectangle)
   - 验证 (diamond)
   - 登录成功 (rectangle) - 右分支
   - 显示错误 (rectangle) - 左分支
   - 结束 (ellipse)

3. 计算坐标并依次创建:
```
create_flowchart_node(label="开始", node_type="ellipse", x=400, y=50)
  → element_id: ellipse_a1b2

create_flowchart_node(label="输入账号密码", node_type="rectangle", x=400, y=180)
  → element_id: rectangle_c3d4

create_flowchart_node(label="验证", node_type="diamond", x=400, y=330)
  → element_id: diamond_e5f6

create_flowchart_node(label="登录成功", node_type="rectangle", x=620, y=530)
  → element_id: rectangle_g7h8

create_flowchart_node(label="显示错误", node_type="rectangle", x=180, y=530)
  → element_id: rectangle_i9j0

create_flowchart_node(label="结束", node_type="ellipse", x=400, y=680)
  → element_id: ellipse_k1l2
```

4. 连接节点:
```
connect_nodes(from_id="ellipse_a1b2", to_id="rectangle_c3d4")
connect_nodes(from_id="rectangle_c3d4", to_id="diamond_e5f6")
connect_nodes(from_id="diamond_e5f6", to_id="rectangle_g7h8", label="是")
connect_nodes(from_id="diamond_e5f6", to_id="rectangle_i9j0", label="否")
connect_nodes(from_id="rectangle_g7h8", to_id="ellipse_k1l2")
connect_nodes(from_id="rectangle_i9j0", to_id="ellipse_k1l2")
```

5. 返回结果摘要

## 扩展指南

### 添加新工具

1. 定义参数 Schema:
```python
class MyToolArgs(BaseModel):
    param1: str = Field(..., description="参数描述")
```

2. 注册工具:
```python
@registry.register("my_tool", "工具描述", MyToolArgs)
async def my_tool(param1: str, context: AgentContext = None):
    # 实现逻辑
    return {"status": "success", ...}
```

3. 工具会自动被 Agent 加载和使用

### 添加新 Agent

1. 继承 BaseAgent 或 PlanningAgent
2. 定义系统提示词
3. 注册所需工具
4. 可选: 重写 `run()` 方法添加自定义逻辑

```python
class MyAgent(PlanningAgent):
    def __init__(self, llm_client):
        super().__init__(
            name="MyAgent",
            role="专家角色",
            llm_client=llm_client,
            system_prompt=MY_SYSTEM_PROMPT,
        )
        self._register_tools()
```

## 配置说明

### LLM 配置 (`config/config.toml`)

```toml
[llm]
provider = "openai"
api_key = "sk-..."
base_url = "https://api.openai.com/v1"
model = "gpt-4"

[llm.fallback]
provider = "deepseek"
api_key = "sk-..."
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

### Agent 参数

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| max_iterations | 15 | 最大 ReAct 循环次数 |
| temperature | 0.3 | LLM 温度 (TeacherAgent) |
| temperature | 0.2 | LLM 温度 (PainterAgent，更低以保证一致性) |

## 常见问题

### Q: 为什么流程图节点位置不准确?

A: 检查 PainterAgent 的系统提示词中的坐标计算示例是否与 LayoutConfig 配置一致。LLM 会参考示例进行坐标计算。

### Q: 如何支持更复杂的图表类型?

A: 可以扩展 PainterAgent 的系统提示词，添加新图表类型的绘制规则，或创建专门的 Agent 处理特定图表。

### Q: 工具调用失败如何处理?

A: Agent 会在 Observation 阶段收到错误信息，并在下一次 Think 中尝试修正。如果持续失败，会在达到 max_iterations 后返回错误。

