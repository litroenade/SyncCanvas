# SyncCanvas 开发文档

> 更新时间: 2025-12-15

---

## 一、项目概述

**SyncCanvas** 是一个基于 CRDT (无冲突复制数据类型) 的**实时协作白板系统**，集成了 **AI Agent 辅助编辑**能力。

### 核心特性

| 特性           | 描述                                             |
| -------------- | ------------------------------------------------ |
| **实时协作**   | 基于 Yjs/pycrdt 的无冲突多用户编辑               |
| **AI 辅助**    | 自然语言驱动的图形生成 (ReAct 架构)              |
| **版本控制**   | Git 式的 Commit/Update 存储机制                  |
| **持久化**     | SQLite 统一存储 + Yjs 增量同步                   |
| **跨平台**     | 支持 PC 和移动端自适应 UI                        |

---

## 二、技术架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (React)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Excalidraw │  │   Zustand   │  │ y-websocket │  │ React Query│ │
│  │  (Canvas)   │  │   (State)   │  │   (CRDT)    │  │   (API)    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬─────┘ │
└─────────┼────────────────┼────────────────┼────────────────┼───────┘
          │                │                │                │
          │ HTTP/REST      │                │ WebSocket      │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Routers   │  │  AI Agent   │  │pycrdt-ws   │  │  YStore    │ │
│  │ (REST API)  │  │  (ReAct)    │  │(Yjs Sync)   │  │ (持久化)   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬─────┘ │
│         │                │                │                │       │
│         └────────────────┴────────────────┴────────────────┘       │
│                                   │                                 │
│                                   ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      SQLite (SQLModel)                       │   │
│  │   Room | Commit | Update | AgentRun | AgentAction | Users   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈详解

#### 后端 (Python 3.12+)

| 技术               | 版本     | 用途                     |
| ------------------ | -------- | ------------------------ |
| **FastAPI**        | 0.121+   | Web 框架 + REST API      |
| **pycrdt**         | 0.12+    | Python CRDT 实现         |
| **pycrdt-websocket** | 0.16+ | Yjs WebSocket 同步服务   |
| **SQLModel**       | 0.0.14+  | ORM (SQLAlchemy + Pydantic) |
| **OpenAI SDK**     | 2.8+     | LLM API 调用             |
| **Jinja2**         | 3.1+     | Prompt 模板渲染          |
| **grandalf**       | 0.8+     | 图布局算法               |

#### 前端 (Node.js + pnpm)

| 技术               | 版本   | 用途                     |
| ------------------ | ------ | ------------------------ |
| **React**          | 18.x   | UI 框架                  |
| **TypeScript**     | 5.x    | 类型系统                 |
| **Vite**           | 6.x    | 构建工具                 |
| **Excalidraw**     | 0.18+  | 白板 Canvas 组件         |
| **Yjs**            | 13.x   | CRDT 客户端              |
| **y-websocket**    | 1.5+   | Yjs WebSocket Provider   |
| **Zustand**        | 5.x    | 状态管理                 |
| **TanStack Query** | 5.x    | 服务端状态管理           |
| **Tailwind CSS**   | 4.x    | 样式框架                 |
| **Framer Motion**  | 12.x   | 动画库                   |

---

## 三、目录结构

```
SyncCanvas/
├── main.py                 # 🚀 应用入口，FastAPI 服务器
├── config/                 # ⚙️ 配置目录
│   └── config.toml         # 主配置文件
├── pyproject.toml          # Python 项目配置 (uv)
├── requirements.txt        # Python 依赖列表
├── uv.lock                 # uv 锁定文件
│
├── src/                    # 📦 后端源代码
│   ├── __init__.py
│   ├── config.py           # 配置加载 (Pydantic 模型)
│   ├── logger.py           # 日志配置 (Rich/structlog)
│   ├── deps.py             # FastAPI 依赖注入
│   │
│   ├── agent/              # 🤖 AI Agent 模块
│   │   ├── __init__.py
│   │   ├── agents/         # Agent 实现
│   │   │   ├── planner.py  # PlannerAgent (主协调)
│   │   │   └── canvaser.py # CanvaserAgent (绘图专家)
│   │   ├── core/           # 核心组件
│   │   │   ├── agent.py    # BaseAgent 基类 + ReAct 循环
│   │   │   ├── llm.py      # LLM 客户端 (主备故障转移)
│   │   │   ├── tools.py    # 工具注册器
│   │   │   ├── errors.py   # 错误定义
│   │   │   ├── json_parser.py      # JSON 解析/修复
│   │   │   ├── state_machine.py    # Agent 状态机
│   │   │   └── error_recovery.py   # 错误恢复策略
│   │   ├── prompts/        # Prompt 模板 (Jinja2)
│   │   └── tools/          # 画布操作工具
│   │       ├── canvas.py       # 画布查询
│   │       ├── elements.py     # 元素 CRUD
│   │       ├── flowchart.py    # 流程图节点
│   │       ├── architecture.py # 架构图组件
│   │       ├── sequence.py     # 时序图
│   │       ├── auto_layout.py  # 自动布局
│   │       ├── presets.py      # 预设样式
│   │       ├── schemas.py      # 工具 Schema
│   │       ├── helpers.py      # 辅助函数
│   │       ├── general_tools.py    # 通用工具
│   │       ├── text_tools.py       # 文本处理
│   │       └── web_tools.py        # 网页工具
│   │
│   ├── auth/               # 🔐 认证模块
│   │   ├── router.py       # 认证路由
│   │   └── utils.py        # JWT 工具
│   │
│   ├── db/                 # 💾 数据库模块
│   │   ├── database.py     # 数据库连接
│   │   ├── models.py       # SQLModel 模型
│   │   ├── crud.py         # CRUD 操作
│   │   ├── user.py         # 用户相关
│   │   ├── base.py         # 基础工具
│   │   └── ystore.py       # Yjs 持久化 (YStore)
│   │
│   ├── routers/            # 🌐 API 路由
│   │   ├── ai.py           # AI 相关路由
│   │   ├── config.py       # 配置管理路由
│   │   ├── rooms.py        # 房间管理
│   │   ├── upload.py       # 文件上传
│   │   └── version_control/# 版本控制 (IGit)
│   │
│   ├── services/           # 📋 业务逻辑
│   │   ├── agent_runs.py   # Agent 运行记录
│   │   └── igit.py         # IGit 服务
│   │
│   ├── ws/                 # 🔌 WebSocket 模块
│   │   ├── sync.py         # Yjs 同步服务
│   │   └── message_router.py # 发布/订阅
│   │
│   └── utils/              # 🛠️ 工具模块
│       └── async_task.py   # 异步任务管理
│
├── frontend/               # 🎨 前端源代码
│   ├── src/
│   │   ├── App.tsx             # 应用入口
│   │   ├── main.tsx            # React 挂载
│   │   ├── index.css           # 全局样式
│   │   ├── components/         # UI 组件
│   │   │   ├── ai/             # AI 相关组件
│   │   │   ├── canvas/         # Canvas 组件
│   │   │   └── common/         # 通用组件
│   │   ├── pages/              # 页面
│   │   │   ├── Login.tsx       # 登录页
│   │   │   ├── Rooms.tsx       # 房间列表
│   │   │   ├── Settings.tsx    # 设置页
│   │   │   └── Welcome.tsx     # 欢迎页
│   │   ├── stores/             # Zustand 状态
│   │   │   ├── connection_store.ts
│   │   │   ├── history_store.ts
│   │   │   ├── preferences_store.ts
│   │   │   └── useThemeStore.ts
│   │   ├── hooks/              # React Hooks
│   │   ├── services/api/       # API 服务
│   │   ├── config/             # 前端配置
│   │   ├── lib/                # 工具库
│   │   ├── styles/             # 样式文件
│   │   ├── types/              # TypeScript 类型
│   │   └── utils/              # 工具函数
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── data/                   # 📁 数据目录
│   ├── sync_canvas.db      # SQLite 数据库
│   └── images/             # 上传的图片
│
├── docs/                   # 📚 文档
│   ├── ai_agent.md         # AI Agent 架构
│   ├── development.md      # 开发文档 (本文件)
│   ├── features.md         # 功能说明
│   └── todo.md             # 开发计划
│
└── logs/                   # 📝 日志目录
```

---

## 四、核心模块详解

### 4.1 AI Agent 系统

Agent 系统采用 **ReAct (Reasoning + Acting)** 架构：

```
User Input → PlannerAgent
                ↓
        关键词匹配: "画/流程图/架构图"?
                ↓
    ├── YES → CanvaserAgent (专业绘图)
    └── NO  → PlannerAgent 自己处理

        ↓
    ReAct Loop: THINK → ACT → OBSERVE
        ↓
    Yjs 写入 → WebSocket 广播 → 前端渲染
```

#### Agent 类型

| Agent             | 文件              | 职责                                 |
| ----------------- | ----------------- | ------------------------------------ |
| **BaseAgent**     | `core/agent.py`   | 基类，实现 ReAct 循环、重试、超时    |
| **PlannerAgent**  | `agents/planner.py` | 主协调者，理解用户意图，分发任务     |
| **CanvaserAgent** | `agents/canvaser.py` | 专业绘图，处理复杂图表生成           |

#### 工具系统

工具通过 `@register_tool` 装饰器注册：

```python
from src.agent.core.tools import register_tool

@register_tool(name="create_element", description="创建画布元素")
def create_element(ctx: AgentContext, element_type: str, x: float, y: float, ...):
    # 工具实现
    pass
```

| 工具类别     | 文件                | 主要工具                                     |
| ------------ | ------------------- | -------------------------------------------- |
| **画布查询** | `canvas.py`         | `get_canvas_bounds`, `list_elements`         |
| **元素操作** | `elements.py`       | `create_element`, `update_element`, `delete` |
| **流程图**   | `flowchart.py`      | `create_flowchart_node`, `connect_nodes`     |
| **架构图**   | `architecture.py`   | `create_architecture_node`                   |
| **时序图**   | `sequence.py`       | `create_sequence_diagram`                    |
| **自动布局** | `auto_layout.py`    | `auto_layout`, `force_directed_layout`       |

### 4.2 实时协作系统

基于 **CRDT (Conflict-free Replicated Data Type)** 实现无冲突多用户编辑：

```
Client A ──┐
           │    ┌─────────────────┐    ┌──────────┐
Client B ──┼────│ pycrdt-websocket│────│  YStore  │────→ SQLite
           │    │  (Yjs 同步)      │    │  (持久化) │
Client C ──┘    └─────────────────┘    └──────────┘
```

#### 关键组件

| 组件                  | 文件                  | 功能                           |
| --------------------- | --------------------- | ------------------------------ |
| **WebSocketServer**   | `ws/sync.py`          | pycrdt-websocket 服务器        |
| **WebSocketASGI**     | `ws/sync.py`          | ASGI 适配器                    |
| **YStore**            | `db/ystore.py`        | Yjs 持久化到 SQLite            |
| **MessageRouter**     | `ws/message_router.py`| 发布/订阅消息路由              |

### 4.3 数据库模型

```
┌─────────────────┐     ┌─────────────────┐
│      Room       │     │      Users      │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │────→│ id (PK)         │
│ name            │     │ username        │
│ owner_id (FK)   │←────│ password_hash   │
│ head_commit_id  │     └─────────────────┘
│ is_public       │
│ created_at      │
└────────┬────────┘
         │
         │ 1:N
         ↓
┌─────────────────┐     ┌─────────────────┐
│     Commit      │     │     Update      │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │
│ room_id (FK)    │     │ room_id (FK)    │
│ parent_id       │     │ data (bytes)    │
│ data (bytes)    │     │ timestamp       │
│ hash            │     └─────────────────┘
│ author_name     │
│ message         │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│    AgentRun     │     │  AgentAction    │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │←────│ run_id (FK)     │
│ room_id         │     │ tool            │
│ prompt          │     │ arguments (JSON)│
│ model           │     │ result (JSON)   │
│ status          │     │ created_at      │
│ message         │     └─────────────────┘
└─────────────────┘
```

### 4.4 版本控制 (IGit)

类似 Git 的版本控制机制：

| 概念               | Git 类比   | 说明                         |
| ------------------ | ---------- | ---------------------------- |
| **Commit**         | Commit     | 完整状态快照 (二进制)        |
| **Update**         | Diff       | 增量变更 (Yjs Update)        |
| **head_commit_id** | HEAD       | 房间当前版本指针             |

**工作流程：**

1. 用户操作 → Yjs Update → 写入 `Update` 表
2. 用户离开 / 空闲超时 → 触发自动 Commit
3. 合并所有 Update → 创建新 Commit
4. 更新 `head_commit_id` → 清理旧 Update

---

## 五、API 端点

### 5.1 REST API

所有 API 使用 `/api` 前缀。

#### 认证

| 方法   | 端点            | 描述         |
| ------ | --------------- | ------------ |
| `POST` | `/api/auth/token` | 登录获取 JWT |

#### 房间管理

| 方法     | 端点                   | 描述       |
| -------- | ---------------------- | ---------- |
| `GET`    | `/api/rooms`           | 房间列表   |
| `POST`   | `/api/rooms`           | 创建房间   |
| `GET`    | `/api/rooms/{room_id}` | 房间详情   |
| `DELETE` | `/api/rooms/{room_id}` | 删除房间   |

#### AI Agent

| 方法   | 端点                         | 描述         |
| ------ | ---------------------------- | ------------ |
| `POST` | `/api/ai/generate`           | AI 生成请求  |
| `GET`  | `/api/ai/runs/{room_id}`     | 运行历史     |
| `GET`  | `/api/ai/runs/{run_id}/detail` | 运行详情   |
| `POST` | `/api/ai/runs/{run_id}/cancel` | 取消运行   |
| `GET`  | `/api/ai/tools`              | 工具列表     |

#### 版本控制

| 方法   | 端点                                  | 描述       |
| ------ | ------------------------------------- | ---------- |
| `GET`  | `/api/rooms/{room_id}/commits`        | 提交历史   |
| `POST` | `/api/rooms/{room_id}/commits`        | 创建提交   |
| `POST` | `/api/rooms/{room_id}/commits/revert` | 回滚版本   |

#### 配置管理

| 方法   | 端点          | 描述         |
| ------ | ------------- | ------------ |
| `GET`  | `/api/config` | 获取配置     |
| `PUT`  | `/api/config` | 更新配置     |

### 5.2 WebSocket

| 端点            | 描述                       |
| --------------- | -------------------------- |
| `WS /ws/{room_id}` | Yjs 文档同步 (pycrdt-websocket) |

---

## 六、配置系统

### 6.1 配置文件

配置文件位于 `config/config.toml`：

```toml
version = "0.1.1"

[security]
secret_key = "..."  # 自动生成，用于 JWT 签名

[server]
host = "0.0.0.0"
port = 8000
allowed_origins = ["*"]

[database]
url = "sqlite:///./data/sync_canvas.db"
echo = false

[ai]
provider = "siliconflow"
model = "deepseek-v3"
base_url = "https://api.siliconflow.cn/v1"
api_key = "sk-..."
temperature = 0.3
max_tokens = 4096
tool_choice = "auto"
max_tool_calls = 10

[ai.fallback]  # 备用模型配置
provider = "openai"
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."

[logging]
level = "INFO"
colorize = true
agent_level = "DEBUG"
```

### 6.2 配置模型

配置使用 Pydantic 模型，支持类型验证和 UI 元数据：

```python
class AIProviderConfig(BaseModel):
    provider: str = Field(default="siliconflow", title="主模型提供商")
    model: str = Field(default="deepseek-v3", title="模型名称")
    base_url: str = Field(...)
    api_key: str = Field(
        ...,
        json_schema_extra=ExtraField(is_secret=True).model_dump()
    )
```

---

## 七、开发环境搭建

### 7.1 前置要求

- **Python**: 3.12+
- **Node.js**: 18+ (推荐使用 pnpm)
- **uv**: Python 包管理器

### 7.2 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd SyncCanvas

# 2. 安装后端依赖
uv sync

# 3. 安装前端依赖
cd frontend
pnpm install
cd ..

# 4. 启动开发服务器
# 后端 (Terminal 1)
uv run python main.py

# 前端 (Terminal 2)
cd frontend
pnpm dev
```

### 7.3 生产模式

```bash
# 构建前端
cd frontend
pnpm build
cd ..

# 启动服务器 (自动服务静态文件)
uv run python main.py
```

服务器启动在 `http://127.0.0.1:8021`

### 7.4 登录

使用 `config/config.toml` 中的 `secret_key` 作为密码：

- **用户名**: 任意
- **密钥**: security.secret_key

---

## 八、开发规范

### 8.1 代码风格

#### Python

- 使用 **Ruff** 进行代码检查和格式化
- 遵循 PEP 8 规范
- 使用类型注解

```bash
# 运行 Ruff 检查
ruff check src/

# 自动修复
ruff check --fix src/
```

#### TypeScript

- 使用 **ESLint** + **Prettier**
- 使用严格的 TypeScript 配置

```bash
# 运行 ESLint
cd frontend
pnpm lint
```

### 8.2 Git 提交规范

使用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

# 示例
feat(agent): 添加自动布局工具
fix(canvas): 修复元素重叠问题
docs(readme): 更新快速开始指南
refactor(llm): 重构 LLM 客户端
```

### 8.3 测试

```bash
# 运行后端测试
uv run pytest

# 运行前端测试
cd frontend
pnpm test
```

---

## 九、常见问题

### Q1: 前端构建目录不存在

**现象**: 启动后端时提示 `frontend/dist` 不存在

**解决**: 后端会自动尝试构建前端，或手动执行：

```bash
cd frontend
pnpm install
pnpm build
```

### Q2: WebSocket 连接失败

**现象**: 前端无法连接到 WebSocket

**检查**:
1. 确认后端已启动
2. 检查 CORS 配置 (`config.toml` 中的 `allowed_origins`)
3. 确认端口号匹配

### Q3: AI 生成失败

**现象**: AI 请求返回错误

**检查**:
1. 验证 `config.toml` 中的 AI 配置
2. 确认 API Key 有效
3. 查看后端日志获取详细错误信息

### Q4: 数据库迁移

**现象**: 数据库结构更新后无法启动

**解决**: 删除旧数据库文件 (会丢失数据):

```bash
rm data/sync_canvas.db
```

---

## 十、参考文档

- [AI Agent 架构](./ai_agent.md) - Agent 系统详细设计
- [功能说明](./features.md) - 功能特性列表
- [开发计划](./todo.md) - 未来开发计划

---

## 十一、贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request
