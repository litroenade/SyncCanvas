# SyncCanvas - 协作白板

一个基于 WebSocket 和 CRDT 的实时协作白板应用。

## 项目结构

```
SyncCanvas/
├── main.py                 # 应用入口，FastAPI 服务器
├── config.toml             # 配置文件
├── pyproject.toml          # Python 项目配置 (uv)
├── requirements.txt        # Python 依赖列表
├── uv.lock                 # uv 锁定文件
│
├── src/                    # 后端源代码
│   ├── __init__.py
│   ├── config.py           # 配置加载
│   ├── logger.py           # 日志配置
│   │
│   ├── auth/               # 认证模块
│   │   ├── __init__.py
│   │   ├── router.py       # 认证路由 (登录/注册)
│   │   └── utils.py        # JWT 工具函数
│   │
│   ├── crdt/               # CRDT 模块 (预留)
│   │   └── __init__.py
│   │
│   ├── db/                 # 数据库模块
│   │   ├── __init__.py
│   │   ├── crud.py         # CRUD 操作
│   │   ├── database.py     # 数据库连接
│   │   ├── models.py       # SQLModel 模型 (Commit, Update, Room, User)
│   │   └── ystore.py       # 自定义 YStore (SQLModel 持久化)
│   │
│   ├── models/             # Pydantic 模型
│   │   ├── __init__.py
│   │   └── user.py         # 用户模型
│   │
│   ├── routers/            # API 路由
│   │   ├── __init__.py
│   │   ├── ai.py           # AI 相关路由
│   │   ├── rooms.py        # 房间管理路由
│   │   ├── upload.py       # 文件上传路由
│   │   └── igit/           # IGit 版本控制路由
│   │       ├── __init__.py
│   │       ├── models.py   # IGit 请求/响应模型
│   │       ├── router.py   # IGit 路由
│   │       └── utils.py    # IGit 工具函数
│   │
│   ├── services/           # 业务逻辑服务
│   │   └── igit.py         # IGit 版本控制服务
│   │
│   └── ws/                 # WebSocket 模块
│       ├── __init__.py
│       └── sync.py         # Yjs 同步服务 (pycrdt-websocket)
│
├── frontend/               # 前端源代码 (React + TypeScript)
│   ├── index.html          # HTML 入口
│   ├── package.json        # npm 依赖
│   ├── pnpm-lock.yaml      # pnpm 锁定文件
│   ├── vite.config.ts      # Vite 配置
│   ├── tsconfig.json       # TypeScript 配置
│   ├── tailwind.config.js  # Tailwind CSS 配置
│   ├── postcss.config.js   # PostCSS 配置
│   ├── eslint.config.js    # ESLint 配置
│   │
│   ├── dist/               # 构建输出 (由后端静态服务)
│   │
│   └── src/
│       ├── main.tsx        # React 入口
│       ├── App.tsx         # 应用主组件 (路由配置)
│       ├── index.css       # 全局样式
│       │
│       ├── components/     # UI 组件
│       │   ├── AIGenerateModal.tsx # AI 生成弹窗
│       │   ├── Canvas.tsx          # 画布主组件 (Konva)
│       │   ├── CommitDiffPanel.tsx # 提交差异面板
│       │   ├── ContextMenu.tsx     # 右键菜单
│       │   ├── Cursors.tsx         # 远程光标显示
│       │   ├── ElementsPanel.tsx   # 元素面板
│       │   ├── ExportButtons.tsx   # 导出按钮
│       │   ├── Grid.tsx            # 网格背景
│       │   ├── HistoryPanel.tsx    # 历史版本面板
│       │   ├── Modal.tsx           # 通用弹窗组件
│       │   ├── PropertiesPanel.tsx # 属性面板
│       │   ├── SettingsModal.tsx   # 设置弹窗
│       │   ├── Sidebar.tsx         # 侧边栏
│       │   ├── Toolbar.tsx         # 工具栏
│       │   ├── WelcomeModal.tsx    # 欢迎弹窗
│       │   └── ZoomControls.tsx    # 缩放控件
│       │
│       ├── stores/         # Zustand 状态管理
│       │   ├── connection_store.ts # 连接状态
│       │   ├── history_store.ts    # 历史记录
│       │   ├── preferences_store.ts# 用户偏好
│       │   ├── useCanvasStore.ts   # 画布状态
│       │   └── useThemeStore.ts    # 主题状态
│       │
│       ├── hooks/          # React Hooks
│       │   ├── useYjs.ts           # Yjs 同步 Hook
│       │   └── use_websocket.ts    # WebSocket Hook
│       │
│       ├── lib/            # 工具库
│       │   ├── d3-layout.ts        # D3 布局算法
│       │   ├── utils.ts            # 通用工具
│       │   └── yjs.ts              # Yjs 房间管理器
│       │
│       ├── pages/          # 页面组件
│       │   ├── Login.tsx           # 登录页
│       │   └── Rooms.tsx           # 房间列表页
│       │
│       ├── services/       # API 服务
│       │   └── api/
│       │       ├── ai.ts           # AI API 调用
│       │       └── rooms.ts        # 房间 API 调用
│       │
│       ├── config/         # 前端配置
│       │   ├── env.ts              # 环境变量
│       │   └── tool_icon_sets.ts   # 工具图标
│       │
│       ├── types/          # TypeScript 类型
│       │   └── index.ts
│       │
│       └── utils/          # 工具函数
│           ├── export.ts           # 导出功能
│           ├── smooth_stroke.ts    # 平滑笔画
│           └── websocket.ts        # WebSocket 工具
│
├── data/                   # 数据目录
│   ├── settings.json       # 服务器配置 (含 secret_key)
│   ├── sync_canvas.db      # SQLite 数据库
│   └── images/             # 上传的图片
│
├── docs/                   # 文档
│   ├── features.md         # 功能说明
│   └── todo.md             # 待办事项
│
└── logs/                   # 日志目录
    └── app.log             # 应用日志
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
