# SyncCanvas - 协作白板

一个基于 WebSocket 和 CRDT 的实时协作白板应用。

## 项目结构

```
SyncCanvas/
├── main.py                 # 应用入口，FastAPI 服务器
├── config/                 # 配置目录
│   └── config.toml         # 主配置文件
├── pyproject.toml          # Python 项目配置 (uv)
├── requirements.txt        # Python 依赖列表
├── uv.lock                 # uv 锁定文件
│
├── src/                    # 后端源代码
│   ├── __init__.py
│   ├── config.py           # 配置加载
│   ├── logger.py           # 日志配置
│   ├── deps.py             # FastAPI 依赖注入
│   │
│   ├── agent/              # AI Agent 模块 ⭐
│   │   ├── base.py         # BaseAgent 基类 + 状态机
│   │   ├── llm.py          # LLM 客户端
│   │   ├── errors.py       # 错误定义 + JSON 解析
│   │   ├── registry.py     # 工具注册表
│   │   ├── planner.py      # PlannerAgent (主协调)
│   │   ├── canvaser.py     # CanvaserAgent (绘图专家)
│   │   │
│   │   ├── pipeline/       # 5-Phase 执行管道
│   │   │   ├── executor.py # 主编排器
│   │   │   ├── cognition.py# 状态水合
│   │   │   ├── router.py   # 意图路由
│   │   │   ├── reasoning.py# 推理层
│   │   │   ├── layout.py   # 布局引擎
│   │   │   └── transaction.py
│   │   │
│   │   ├── canvas/         # 画布模型
│   │   │   ├── model.py    # 元素模型
│   │   │   └── commands.py # 控制命令
│   │   │
│   │   ├── prompts/        # Prompt 模板 (Jinja2)
│   │   └── tools/          # 画布操作工具
│   │       ├── elements.py # 元素操作
│   │       ├── flowchart.py# 流程图
│   │       ├── architecture.py
│   │       ├── sequence.py # 时序图
│   │       └── auto_layout.py
│   │
│   ├── auth/               # 认证模块
│   │   ├── router.py       # 认证路由
│   │   └── utils.py        # JWT 工具
│   │
│   ├── db/                 # 数据库模块
│   │   ├── crud.py         # CRUD 操作
│   │   ├── database.py     # 数据库连接
│   │   ├── models.py       # SQLModel 模型
│   │   └── ystore.py       # Yjs 持久化
│   │
│   ├── routers/            # API 路由
│   │   ├── ai.py           # AI 相关路由
│   │   ├── config.py       # 配置管理路由
│   │   ├── rooms.py        # 房间管理
│   │   ├── upload.py       # 文件上传
│   │   └── igit/           # 版本控制
│   │
│   ├── services/           # 业务逻辑
│   │   ├── agent_runs.py   # Agent 运行记录
│   │   └── igit.py         # IGit 服务
│   │
│   └── ws/                 # WebSocket 模块
│       ├── sync.py         # Yjs 同步服务
│       └── message_router.py
│
├── frontend/               # 前端源代码 (React + TypeScript)
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   ├── pages/          # 页面 (Login, Rooms, Settings, Welcome)
│   │   ├── stores/         # Zustand 状态管理
│   │   ├── hooks/          # React Hooks
│   │   ├── services/api/   # API 服务
│   │   └── ...
│   └── ...
│
├── data/                   # 数据目录
│   ├── sync_canvas.db      # SQLite 数据库
│   └── images/             # 上传的图片
│
├── docs/                   # 文档
│   ├── ai_agent.md         # AI Agent 架构文档 ⭐
│   ├── features.md         # 功能说明
│   └── todo.md             # 开发计划
│
└── logs/                   # 日志目录
```

## Quick Start

### 1. Start Backend

```bash
# Backend + Frontend Static Files (Production Mode)
uv run python main.py
```

Server will start at `http://127.0.0.1:8021`.

### 2. Development Mode

```bash
# Backend
uv run python main.py

# Frontend (in another terminal)
cd frontend
pnpm dev
```

### 3. Build Frontend

```bash
cd frontend
pnpm run build
```

Build output goes to `frontend/dist/`, served automatically by backend.

### 4. 登录

使用 `data/settings.json` 中的 `secret_key` 登录：

- 用户名：任意
- 密钥：settings.json 中的 secret_key

## 快捷键

| 快捷键    | 功能                |
| --------- | ------------------- |
| `V` / `1` | 选择工具            |
| `H` / `2` | 手形工具 (移动画布) |
| `R` / `3` | 矩形                |
| `O` / `4` | 圆形                |
| `D` / `5` | 菱形                |
| `A` / `6` | 箭头                |
| `L` / `7` | 线条                |
| `P` / `8` | 画笔 (自由绘制)     |
| `T` / `9` | 文本                |
| `E`       | 橡皮擦              |
| `Ctrl+Z`  | 撤销                |
| `Ctrl+Y`  | 重做                |
| `Delete`  | 删除选中            |
| `Esc`     | 取消 / 返回选择     |
| 鼠标滚轮  | 缩放                |

## 技术栈

**后端:**

- FastAPI
- pycrdt + pycrdt-websocket (CRDT 同步)
- SQLModel + SQLite
- JWT 认证

**前端:**

- React 18 + TypeScript
- Konva (Canvas 渲染)
- Yjs + y-websocket (CRDT 客户端)
- Zustand (状态管理)
- Tailwind CSS


synvcanvas is maybe a  try of natural language to get the better task . We don't take attention to the llm's activity to transform the language to mermaid or the tuple . We want it can control the canvas that have existed by returning the elements, thus we need to refactor the way to the excalidraw to save . This sound like the drawio , it usually use mycell to store all the information in the canvas , so what we build may be like it .Of course , drawio is not supported to mutilple people to sync work in together , so we solve this as the same time . 

control elements and not generate.

