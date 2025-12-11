# SyncCanvas 功能文档

> 更新时间: 2025-12-11

## 项目概述

SyncCanvas 是一个基于 CRDT 的实时协作白板系统，集成了 AI Agent 辅助编辑能力。系统采用 **State-Aware Neuro-Symbolic Pipeline** 架构，实现智能化的协作白板体验。

**核心特性：**
- 🔄 **实时协作** - 基于 CRDT 的无冲突多用户编辑
- 🤖 **AI 辅助** - 自然语言驱动的图形生成和编辑
- 📊 **神经符号架构** - LLM 负责逻辑，算法负责布局
- 💾 **持久化存储** - Git 式增量存储策略

---

## 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 运行环境 |
| FastAPI | 0.115+ | Web 框架 |
| pycrdt-websocket | 0.15+ | Yjs 兼容 CRDT 服务 |
| SQLModel | 0.0.22+ | ORM (SQLAlchemy + Pydantic) |
| SQLite | 3.x | 数据库 |
| OpenAI SDK | 1.x | LLM 调用 |
| Jinja2 | 3.x | Prompt 模板 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.x | UI 框架 |
| TypeScript | 5.x | 类型系统 |
| Vite | 6.x | 构建工具 |
| Excalidraw | 0.18+ | Canvas 组件 |
| Yjs | 13.x | CRDT 客户端 |
| Zustand | 5.x | 状态管理 |

---

## 核心功能模块

### 1. 实时协作系统 (CRDT)

基于 Yjs/pycrdt 实现的无冲突复制数据类型：

```
┌─────────────────────────────────────────────────────────────────┐
│                    CRDT 同步架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Client A ──┐                                                 │
│              │    ┌─────────────────┐                          │
│   Client B ──┼────│  WebSocket Hub  │────┐                     │
│              │    │  (pycrdt-ws)    │    │                     │
│   Client C ──┘    └─────────────────┘    │                     │
│                           │              │                     │
│                           ▼              ▼                     │
│                   ┌─────────────┐  ┌──────────┐               │
│                   │   YDoc      │  │  SQLite  │               │
│                   │  (内存)     │  │ (持久化) │               │
│                   └─────────────┘  └──────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**特性：**
- 多用户同时编辑，自动合并冲突 (Last-Write-Wins)
- 低延迟实时同步 (<100ms)
- 支持离线编辑，重连后自动同步
- 房间级并发锁，防止 Agent 冲突

### 2. AI Agent 系统

#### 架构概述

采用 **黑板模式 (Blackboard Pattern)**：
- **黑板** = Yjs/CRDT 共享数据 (Canvas State)
- **专家** = 用户 + AI Agent，都能读写黑板

```
┌─────────────────────────────────────────────────────────────────┐
│                    黑板模式架构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│     用户 (Expert)          AI Agent (Expert)                   │
│         │                       │                              │
│         ▼                       ▼                              │
│    ┌─────────────────────────────────────────┐                 │
│    │            Yjs 文档 (黑板)              │                 │
│    │  ┌─────────────────────────────────┐   │                 │
│    │  │  elements: [node_A, node_B, ...]│   │                 │
│    │  │  edges: [A→B, B→C, ...]         │   │                 │
│    │  └─────────────────────────────────┘   │                 │
│    └─────────────────────────────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Agent 类型

| Agent | 文件 | 职责 |
|-------|------|------|
| **PlannerAgent** | `agents/planner.py` | 主协调者，理解用户意图，简单任务直接处理 |
| **CanvaserAgent** | `agents/canvaser.py` | 专业绘图，处理复杂流程图/架构图 |
| **BaseAgent** | `core/agent.py` | ReAct 循环基类，提供重试/超时控制 |

#### ReAct 循环

```
┌─────────────────────────────────────────────────────────────────┐
│                    ReAct 执行循环                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. THINK (思考)                                               │
│      │  LLM 分析当前状态和用户请求                              │
│      ▼                                                          │
│   2. ACT (行动)                                                 │
│      │  选择并调用工具 (create_node, connect, etc.)             │
│      ▼                                                          │
│   3. OBSERVE (观察)                                             │
│      │  获取工具执行结果                                        │
│      ▼                                                          │
│   4. 重复直到任务完成或达到最大步数                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 工具系统

| 类别 | 工具 | 说明 |
|------|------|------|
| **画布查询** | `get_canvas_bounds` | 获取画布边界和建议位置 |
| **画布查询** | `list_elements` | 列出所有元素 |
| **元素操作** | `create_element` | 创建基础图形 |
| **元素操作** | `update_element` | 更新元素属性 |
| **元素操作** | `delete_elements` | 删除元素 |
| **流程图** | `create_flowchart_node` | 创建流程图节点 |
| **流程图** | `connect_nodes` | 连接节点 |
| **布局** | `auto_layout_elements` | 自动布局 |
| **架构图** | `create_architecture_node` | 创建架构节点 |

### 3. 神经符号架构 (Neuro-Symbolic) [计划中]

这是 SyncCanvas 的核心创新，将 LLM 与确定性算法解耦：

```
┌─────────────────────────────────────────────────────────────────┐
│              State-Aware Neuro-Symbolic Pipeline                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: State Hydration (状态注入)                            │
│     │  summarize_graph(ydoc) → 轻量拓扑描述                      │
│     │  构建增强 Prompt: {用户指令, 图摘要, 历史}                  │
│     ▼                                                           │
│  Phase 2: Intent Routing (意图路由)                             │
│     │  Router 分类: create / modify / qa                        │
│     │  分发给对应 Agent                                         │
│     ▼                                                           │
│  Phase 3: Logical Reasoning (逻辑推理) [神经部分]               │
│     │  Generator: 生成逻辑 JSON (无坐标)                        │
│     │  Mutator: 输出操作序列 [add, delete, connect]             │
│     │  Grounding: 指代消解 "那个红框" → node-123                │
│     ▼                                                           │
│  Phase 4: Geometric Solving (几何求解) [符号部分]               │
│     │  LayoutEngine 计算坐标                                    │
│     │  子图增量布局 (保持心智地图稳定)                          │
│     ▼                                                           │
│  Phase 5: Sync & Broadcast (同步广播)                           │
│     │  CRDT Transaction → WebSocket 推送                        │
│     ▼                                                           │
│  [完成]                                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心创新点

**1. 拓扑与几何解耦**

| 现状 | 目标 |
|------|------|
| LLM 输出 `create_node(x=100, y=200)` | LLM 输出 `add_node(label="A", parent="root")` |
| 坐标不可靠，经常重叠 | 坐标由布局算法计算，保证正确 |

**2. 状态注入 (State Hydration)**

```python
def summarize_graph(ydoc) -> str:
    """将画布转为轻量拓扑描述，不含坐标"""
    # 输出: "Nodes: [A(start), B(process)], Edges: [A→B]"
```

**3. 指代消解 (Grounding)**

用户说："在左边那个红框下面加一个圆"
- 传统方法：LLM 猜测坐标 → 经常错误
- Grounding：识别 "左边红框" → 返回具体 node_id

**4. 子图增量布局**

```python
def apply_layout(ops, graph):
    affected = identify_affected_subgraph(ops)  # 只识别受影响节点
    return layout_subgraph(graph, affected)      # 避免全图重排
```

#### 多模型协作

| 任务类型 | 推荐模型 | 特点 |
|----------|----------|------|
| `router` | gpt-4o-mini | 快速意图分类 |
| `generator` | DeepSeek-V3 | 强推理，复杂结构生成 |
| `mutator` | Qwen-14B | 快速响应，增量修改 |
| `grounding` | gpt-4o-mini | 轻量空间推理 |

### 4. 配置系统

#### 三层配置结构 [计划中]

```toml
# 1. API 供应商层
[[api_providers]]
name = "SiliconFlow"
base_url = "https://api.siliconflow.cn/v1"
api_key = "sk-xxx"

# 2. 模型定义层
[[models]]
name = "qwen-14b"
model_identifier = "Qwen/Qwen2.5-14B-Instruct"
api_provider = "SiliconFlow"

# 3. 任务配置层
[model_task_config.planner]
model_list = ["deepseek-v3", "qwen-14b"]  # 优先级列表
temperature = 0.3
```

#### ExtraField 元数据

配置字段支持 UI 渲染提示：

```python
class ExtraField(BaseModel):
    is_secret: bool = False      # 密码框
    is_textarea: bool = False    # 多行文本
    is_hidden: bool = False      # 隐藏字段
    placeholder: str = ""        # 占位符
    ref_model_groups: bool = False  # 模型选择器
```

### 5. 数据持久化

#### 统一数据库设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      sync_canvas.db                              │
├─────────────────────────────────────────────────────────────────┤
│  User        - 用户信息、认证                                    │
│  Room        - 房间配置、访问控制                                │
│  RoomMember  - 房间成员关系                                      │
│  Snapshot    - Yjs 文档完整快照（二进制）                        │
│  Update      - Yjs 增量更新（二进制）                            │
│  AgentRun    - Agent 执行记录                                    │
│  AgentAction - 工具调用日志                                      │
└─────────────────────────────────────────────────────────────────┘
```

#### Git 式存储策略

| 概念 | Git 类比 | 说明 |
|------|----------|------|
| Snapshot | Commit | 完整状态快照 |
| Update | Diff | 增量变更 |
| 压缩 | GC | 合并历史 |

**工作流程：**
1. 用户操作产生 Yjs Update → 写入 `update` 表
2. Update 数量超过阈值 (100) → 触发压缩
3. 所有 Update 合并为一个 Snapshot
4. 删除旧的 Update 和 Snapshot

### 6. 房间管理

- 创建/删除房间
- 房间密码保护 (SHA-256 + Salt)
- 公开/私有房间
- 最大用户数限制
- 成员角色管理 (owner/editor/viewer)
- 房间级 Agent 锁 (防止冲突)

### 7. 用户认证

- 用户名 + 服务端密钥认证
- JWT Token (可配置过期时间)
- 游客访问 (无需登录)

### 8. 绘图工具

| 工具 | 快捷键 | 说明 |
|------|--------|------|
| 选择 | V / 1 | 选择、移动、缩放图形 |
| 手形 | H / 2 | 移动画布 |
| 矩形 | R / 3 | 绘制矩形 |
| 圆形 | O / 4 | 绘制圆形/椭圆 |
| 菱形 | D / 5 | 绘制菱形 |
| 箭头 | A / 6 | 绘制箭头 |
| 直线 | L / 7 | 绘制直线 |
| 画笔 | P / 8 | 自由绘制 |
| 文本 | T / 9 | 添加文本 |
| 橡皮擦 | E | 擦除 |

### 9. 画布功能

- 无限画布
- 缩放/平移 (鼠标滚轮)
- 网格显示
- 撤销/重做 (Ctrl+Z / Ctrl+Y)
- 导出 PNG/SVG/JSON
- 实时光标同步

---

## API 端点

### 认证
- `POST /auth/token` - 登录获取 Token

### 房间
- `GET /rooms` - 获取房间列表
- `POST /rooms` - 创建房间
- `GET /rooms/{room_id}` - 获取房间详情
- `DELETE /rooms/{room_id}` - 删除房间

### AI
- `POST /ai/generate` - AI 生成指令
- `GET /ai/runs/{run_id}` - 获取运行状态
- `POST /ai/runs/{run_id}/cancel` - 取消运行

### 配置 [计划中]
- `GET /config/providers` - 获取供应商列表
- `POST /config/providers` - 添加供应商
- `GET /config/models` - 获取模型列表
- `GET /config/task-config` - 获取任务配置

### WebSocket
- `WS /ws/{room_id}` - Yjs 同步连接

---

## 日志系统

支持分模块日志级别：

```toml
[logging]
level = "INFO"
colorize = true
exclude_frontend = false     # 过滤 WebSocket/Uvicorn 日志
frontend_level = "WARNING"   # 前端模块日志级别
agent_level = "DEBUG"        # Agent 模块日志级别
```

---

## 性能指标

| 指标 | 目标值 |
|------|--------|
| 同步延迟 | < 100ms |
| LLM 响应 | < 5s |
| 工具执行 | < 2s |
| 并发用户 | 50+ / 房间 |

---

## 参考文档

- [AI Agent 架构](./ai_agent.md)
- [开发计划](./todo.md)
