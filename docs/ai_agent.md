# AI Agent 系统文档

> 版本: 1.1.0 | 更新时间: 2024-12

## 概述

SyncCanvas AI Agent 是一个基于 ReAct 架构的智能白板助手，支持：

- 🎨 **智能绘图** - 流程图、架构图、数据流图等
- 💬 **自然对话** - 理解上下文，多轮交互
- 🌐 **信息获取** - 网页爬取、文本分析
- 📐 **画布感知** - 自动获取边界，避免覆盖
- 🔒 **鲁棒架构** - 重试、超时、并发控制

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    AI Service Layer                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │   Teacher    │───▶│   Painter    │                  │
│  │    Agent     │    │    Agent     │                  │
│  └──────┬───────┘    └──────┬───────┘                  │
│         │                    │                          │
│         ▼                    ▼                          │
│  ┌─────────────────────────────────────┐               │
│  │           Tool Registry              │               │
│  ├─────────────────────────────────────┤               │
│  │ • Excalidraw Tools (绘图)           │               │
│  │ • Web Tools (网页爬取)              │               │
│  │ • General Tools (通用)              │               │
│  └─────────────────────────────────────┘               │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    LLM Client                            │
│            (SiliconFlow / OpenAI)                        │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. TeacherAgent (主协调者)

负责理解用户意图，可以：
- 直接回答问题
- 使用工具完成任务
- 将复杂绘图任务委托给 PainterAgent

**委托关键词检测:**
```python
DRAW_KEYWORDS = [
    "draw", "diagram", "flowchart", "sketch",
    "画", "绘制", "流程图", "数据流图", "架构图"
]
```

### 2. PainterAgent (绘图专家)

专门处理绘图任务，特点：
- 低温度 (0.2) 保证一致性
- 详细的布局指南
- 自动获取画布边界

**布局配置:**
```python
class LayoutConfig:
    NODE_WIDTH = 160       # 矩形宽度
    NODE_HEIGHT = 70       # 矩形高度
    DECISION_SIZE = 120    # 菱形尺寸
    VERTICAL_GAP = 80      # 垂直间距
    HORIZONTAL_GAP = 220   # 分支水平间距
```

## 工具系统

### Excalidraw 绘图工具

| 工具名 | 功能 | 主要参数 |
|--------|------|----------|
| `get_canvas_bounds` | 获取画布边界 | - |
| `create_flowchart_node` | 创建流程图节点 | label, node_type, x, y |
| `connect_nodes` | 连接两个节点 | from_id, to_id, label |
| `create_element` | 创建基础图形 | element_type, x, y, width, height |
| `list_elements` | 列出画布元素 | limit |
| `update_element` | 更新元素属性 | element_id, ... |
| `delete_elements` | 删除元素 | element_ids |
| `clear_canvas` | 清空画布 | confirm |

### 网页工具

| 工具名 | 功能 | 主要参数 |
|--------|------|----------|
| `fetch_webpage` | 获取网页内容 | url, extract_text, max_length |
| `search_web` | 搜索网页 (占位) | query, max_results |

### 通用工具

| 工具名 | 功能 | 主要参数 |
|--------|------|----------|
| `get_current_time` | 获取当前时间 | format |
| `calculate` | 数学计算 | expression |
| `create_outline` | 创建大纲 (占位) | topic, depth |
| `thinking` | 思考记录 (占位) | text, analysis_type |

## 工具注册机制

使用装饰器模式注册工具：

```python
from src.ai_engine.core.tools import registry

@registry.register(
    "tool_name",
    "工具描述",
    ArgsModel  # Pydantic 模型定义参数
)
async def tool_name(
    param1: str,
    param2: int = 10,
    context: AgentContext = None,
) -> Dict[str, Any]:
    """工具实现"""
    return {"status": "success", "data": ...}
```

## 绘图流程

### 1. 获取画布边界 (必须)

```python
# Agent 首先调用
result = await get_canvas_bounds(context=ctx)
# 返回:
# {
#     "status": "success",
#     "is_empty": False,
#     "bounds": {"min_x": 100, "max_x": 500, ...},
#     "suggested_start": {"x": 600, "y": 100},
#     "message": "建议从 (600, 100) 开始绘制"
# }
```

### 2. 创建节点

```python
# 根据 suggested_start 创建节点
result = await create_flowchart_node(
    label="开始",
    node_type="ellipse",
    x=600, y=100,  # 使用建议位置
    context=ctx
)
# 返回的 element_id 用于后续连接
element_id = result["element_id"]
```

### 3. 连接节点

```python
await connect_nodes(
    from_id=start_id,
    to_id=step1_id,
    label=None,  # 判断分支时使用 "是"/"否"
    context=ctx
)
```

## 配置

配置文件位于 `config/config.toml`:

```toml
[ai]
provider = "siliconflow"
model = "Qwen/Qwen2.5-14B-Instruct"
base_url = "https://api.siliconflow.cn/v1"
api_key = "your-api-key"

# 备用提供商
fallback_provider = "openai"
fallback_model = "gpt-4o-mini"

# 工具调用配置
tool_choice = "auto"
max_tool_calls = 10
```

## API 接口

### POST /api/ai/generate

生成图形/执行 AI 任务

**请求:**
```json
{
    "prompt": "画一个用户登录流程图",
    "room_id": "uuid-string"
}
```

**响应:**
```json
{
    "status": "success",
    "message": "已创建 6 个节点，5 条连接线",
    "run_id": 123
}
```

### GET /api/ai/runs/{run_id}

获取 Agent 运行详情

**响应:**
```json
{
    "data": {
        "run_id": 123,
        "room_id": "uuid",
        "prompt": "...",
        "status": "completed",
        "actions": [
            {
                "tool": "get_canvas_bounds",
                "arguments": {},
                "result": {"status": "success", ...}
            },
            ...
        ]
    }
}
```

## 扩展指南

### 添加新工具

1. 在 `src/ai_engine/tools/` 创建模块
2. 定义参数 Schema (Pydantic)
3. 使用 `@registry.register` 装饰器
4. 在 `__init__.py` 中导入

```python
# src/ai_engine/tools/my_tools.py
from pydantic import BaseModel, Field
from src.ai_engine.core.tools import registry

class MyToolArgs(BaseModel):
    param: str = Field(..., description="参数描述")

@registry.register("my_tool", "工具描述", MyToolArgs)
async def my_tool(param: str, context=None):
    return {"status": "success", "result": param}
```

### 添加新 Agent

1. 继承 `BaseAgent` 或 `PlanningAgent`
2. 定义系统提示词
3. 注册需要的工具
4. 实现 `run` 方法

```python
from src.ai_engine.core.agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, llm_client):
        super().__init__(
            name="MyAgent",
            role="...",
            llm_client=llm_client,
            system_prompt="...",
        )
        self._register_tools()
    
    async def run(self, context, user_input, temperature=0.3):
        return await super().run(context, user_input, temperature)
```

## 鲁棒性架构

### 重试机制

LLM 调用和工具执行失败时自动重试：

```python
# 配置
AgentConfig(
    max_retries=3,      # 最大重试次数
    retry_delay=1.0,    # 重试间隔
)
```

### 超时控制

多层超时保护：

```python
AgentConfig(
    llm_timeout=60.0,     # LLM 调用超时
    tool_timeout=30.0,    # 工具执行超时
    total_timeout=300.0,  # 总执行超时
)
```

### 并发控制

房间级别锁，防止同一房间同时多个 Agent 操作：

```python
async with RoomLockManager.acquire(room_id):
    # 执行操作
```

### 执行指标

```python
agent.metrics.to_dict()
# {
#     "duration_ms": 1234.5,
#     "total_llm_calls": 3,
#     "total_tool_calls": 5,
#     "total_retries": 1,
#     "avg_llm_latency_ms": 456.7,
#     "errors": []
# }
```

### 工具安全验证

- 参数类型验证 (Pydantic)
- 危险模式检测 (防止代码注入)
- URL 黑名单 (防止 SSRF)

```python
# 自动验证
@registry.register(
    "my_tool",
    "描述",
    ArgsSchema,
    validate_args=True,  # 启用验证
)
```

### 错误类型

统一的错误代码系统：

| 代码 | 名称 | 说明 |
|------|------|------|
| 2001 | LLM_CONNECTION | LLM 连接失败 |
| 2002 | LLM_TIMEOUT | LLM 调用超时 |
| 3001 | TOOL_NOT_FOUND | 工具不存在 |
| 3003 | TOOL_EXECUTION_ERROR | 工具执行错误 |
| 4002 | ROOM_BUSY | 房间正忙 |

## 日志

日志系统支持颜色输出，不同模块显示不同颜色：

- 🔵 **蓝色** - API 路由 (`src.routers`)
- 🟣 **紫色** - AI 引擎 (`src.ai`)
- 🔵 **青色** - WebSocket (`src.ws`)
- 🟡 **黄色** - 数据库 (`src.db`)
- ⚪ **灰色** - Uvicorn

日志格式: `HH:MM:SS [级别] 模块名 消息`

## 故障排查

### 工具调用失败

1. 检查 `context.room_id` 是否正确
2. 确认 WebSocket 房间已创建
3. 查看后端日志获取详细错误

### 元素未显示

1. 检查坐标是否在可视范围
2. 确认 Y.Array 同步正常
3. 刷新前端页面

### LLM 响应异常

1. 检查 API Key 是否有效
2. 查看 `config/config.toml` 配置
3. 尝试切换到备用提供商
