# SyncCanvas 功能文档

> 更新时间: 2025-12-12

## 项目概述

SyncCanvas 是一个基于 CRDT 的实时协作白板系统，集成了 AI Agent 辅助编辑能力。

**核心特性:**

- **实时协作** - 基于 Yjs/CRDT 的无冲突多用户编辑
- **AI 辅助** - 自然语言驱动的图形生成
- **版本控制** - Git 式的 Commit/Update 存储
- **持久化** - SQLite 统一存储

---

## 技术栈

### 后端

| 技术             | 版本    | 用途         |
| ---------------- | ------- | ------------ |
| Python           | 3.12+   | 运行环境     |
| FastAPI          | 0.115+  | Web 框架     |
| pycrdt-websocket | 0.15+   | Yjs 同步服务 |
| SQLModel         | 0.0.22+ | ORM          |
| OpenAI SDK       | 1.x     | LLM API      |
| Jinja2           | 3.x     | Prompt 模板  |

### 前端

| 技术       | 版本  | 用途        |
| ---------- | ----- | ----------- |
| React      | 18.x  | UI 框架     |
| TypeScript | 5.x   | 类型系统    |
| Vite       | 6.x   | 构建工具    |
| Excalidraw | 0.18+ | Canvas 组件 |
| Yjs        | 13.x  | CRDT 客户端 |
| Zustand    | 5.x   | 状态管理    |

---

## 核心功能

### 1. 实时协作

```
Client A ──┐
           │    ┌─────────────┐    ┌──────────┐
Client B ──┼────│ WebSocket   │────│  SQLite  │
           │    │ (pycrdt-ws) │    │ (持久化) │
Client C ──┘    └─────────────┘    └──────────┘
```

**特性:**

- 多用户同时编辑，自动合并冲突 (CRDT)
- 低延迟实时同步 (< 100ms)
- 离线编辑，重连后自动同步
- 房间级并发锁

### 2. AI Agent 系统

#### Agent 类型

| Agent             | 职责                         |
| ----------------- | ---------------------------- |
| **PlannerAgent**  | 主协调者，理解意图，分发任务 |
| **CanvaserAgent** | 专业绘图，处理复杂图表       |

#### 工具系统

| 类别     | 工具                                                  |
| -------- | ----------------------------------------------------- |
| 画布查询 | `get_canvas_bounds`, `list_elements`                  |
| 元素操作 | `create_element`, `update_element`, `delete_elements` |
| 流程图   | `create_flowchart_node`, `connect_nodes`              |
| 批量操作 | `batch_create_elements`                               |
| 架构图   | `create_architecture_node`                            |

#### ReAct 循环

```
1. THINK - LLM 分析当前状态
2. ACT   - 选择并执行工具
3. OBSERVE - 获取执行结果
4. 重复直到完成
```

### 3. 版本控制

| 概念               | Git 类比 | 说明         |
| ------------------ | -------- | ------------ |
| **Commit**         | Commit   | 完整状态快照 |
| **Update**         | Diff     | 增量变更     |
| **head_commit_id** | HEAD     | 当前版本指针 |

**工作流程:**

1. 用户操作 → Yjs Update → 写入 Update 表
2. 最后用户离开 / 空闲超时 → 触发自动 Commit
3. 所有 Update 合并为 Commit
4. 清理旧 Update

### 4. 数据模型

```
Room
├── id, name, owner_id
├── head_commit_id → Commit
└── password_hash, is_public

Commit
├── id, room_id, parent_id
├── data (bytes) - 完整状态
├── hash (7字符)
└── author_name, message

Update
├── id, room_id
├── data (bytes) - 增量
└── timestamp

AgentRun
├── id, room_id, prompt
├── status, message
└── model, created_at

AgentAction
├── id, run_id
├── tool, arguments, result
└── created_at
```

### 5. 配置系统

```toml
[security]
secret_key = "..."

[server]
host = "0.0.0.0"
port = 8000

[database]
url = "sqlite:///./data/sync_canvas.db"

[ai]
provider = "siliconflow"
model = "deepseek-v3"
base_url = "..."
api_key = "..."

[ai.fallback]   # 备用配置
provider = "openai"
model = "gpt-4o"

[logging]
level = "INFO"
agent_level = "DEBUG"
```

---

## API 端点

### 认证

- `POST /auth/token` - 登录

### 房间

- `GET /rooms` - 房间列表
- `POST /rooms` - 创建房间
- `GET /rooms/{room_id}` - 房间详情
- `DELETE /rooms/{room_id}` - 删除房间

### AI

- `POST /ai/generate` - AI 生成
- `GET /ai/runs/{room_id}` - 运行历史
- `GET /ai/runs/{run_id}/detail` - 运行详情
- `POST /ai/runs/{run_id}/cancel` - 取消运行
- `GET /ai/tools` - 工具列表

### WebSocket

- `WS /ws/{room_id}` - Yjs 同步

---

## 快捷键

| 快捷键    | 功能     |
| --------- | -------- |
| `V` / `1` | 选择工具 |
| `H` / `2` | 手形工具 |
| `R` / `3` | 矩形     |
| `O` / `4` | 圆形     |
| `D` / `5` | 菱形     |
| `A` / `6` | 箭头     |
| `L` / `7` | 线条     |
| `P` / `8` | 画笔     |
| `T` / `9` | 文本     |
| `E`       | 橡皮擦   |
| `Ctrl+Z`  | 撤销     |
| `Ctrl+Y`  | 重做     |

---

## 快速开始

### 启动后端

```bash
uv run python main.py
```

服务启动在 `http://127.0.0.1:8021`

### 开发模式

```bash
# 后端
uv run python main.py

# 前端 (另一个终端)
cd frontend
pnpm dev
```

### 构建前端

```bash
cd frontend
pnpm run build
```

---

## 参考

- [AI Agent 架构](./ai_agent.md)
- [开发计划](./todo.md)
