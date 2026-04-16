# SyncCanvas

SyncCanvas 是一个以 Excalidraw 为画布核心、以 FastAPI 为后端、以 Yjs/CRDT 为实时同步基础的 AI 协作白板项目。它既支持多人实时编辑，也支持通过自然语言生成和维护“受管图表”。

## 项目定位

这个项目的核心目标不是“生成一张静态图”，而是让 AI 直接操作可编辑的白板元素，并将结构化图表以 `DiagramSpec -> 渲染结果 -> Y.Doc` 的链路持续维护。

当前代码主线包括：

- 实时协作白板
- 房间与版本历史
- AI 对话侧栏与流式状态反馈
- 受管图表生成、预览、落板、反向同步
- 中英文 i18n
- 深色 / 浅色 / 跟随系统主题

## 当前能力

### 1. 白板与协作

- 基于 Excalidraw 提供画布交互
- 基于 Yjs / pycrdt / WebSocket 提供实时同步
- 支持房间在线人数与协作状态展示
- 支持版本历史、提交、检出、回滚

### 2. AI 能力

- 支持 AI 对话侧栏
- 支持流式返回执行状态和错误信息
- 支持多种图表 family 的受管生成
- 支持 Mermaid 代码预览与落板
- 支持对受管图进行局部编辑后回写 spec

### 3. 图表引擎

- 采用 spec-first 的受管图表管线
- 后端负责结构化 spec、布局、路由、渲染映射
- 当前已包含 workflow、component cluster、layered architecture、transformer stack、react loop、rag pipeline、i* 等图族的布局引擎
- 对缺少显式布局 hint 的图表提供自动推断与回退策略

### 4. 前端体验

- 中英文切换
- 深色主题统一
- 移动端 FAB
- AI 预览卡片
- 协作事件、版本历史等侧边能力

## 当前边界

- 项目目前默认以“单实例本地画布”模式运行。启动时会自动创建固定房间 `Main Canvas` 和本地用户 `local`。
- 认证相关代码仍保留，但登录入口当前默认未启用。
- 上传图片会保存到 `data/images/`。
- 素材库 / 向量索引的后端能力仍在，但上传后自动写入 library 的联动当前是注释状态，前端入口也暂未作为主功能开放。

## 技术栈

### 后端

- Python 3.12+
- FastAPI
- SQLModel / SQLAlchemy
- SQLite
- pycrdt / pycrdt-websocket / pycrdt-store
- OpenAI SDK
- FAISS

### 前端

- React 18
- TypeScript
- Vite
- Excalidraw
- Yjs / y-websocket
- Zustand

## 项目结构

```text
SyncCanvas/
├─ main.py                     # 后端入口
├─ config/                     # 配置文件目录，首次启动会生成 config.toml
├─ data/                       # 本地数据库、上传文件、库索引文件
├─ frontend/                   # React + Vite 前端
├─ src/
│  ├─ api/                     # HTTP 路由与前端静态资源挂载
│  ├─ application/             # 应用服务层：AI、图表、版本控制、library 等
│  ├─ domain/                  # 领域模型与图表引擎
│  ├─ infra/                   # 配置、日志、指标、启动辅助
│  ├─ persistence/             # 数据库模型、仓储、Yjs 持久化
│  └─ realtime/                # WebSocket / Yjs 实时同步服务
└─ tests/                      # 后端测试
```

## 关键目录说明

- `src/api/routers/ai/handlers.py`
  AI 请求、流式消息、会话管理相关接口。
- `src/api/routers/rooms.py`
  房间、成员、图表更新相关接口。
- `src/api/routers/version_control.py`
  版本历史、commit、checkout、revert 相关接口。
- `src/api/routers/upload.py`
  图片上传、读取、删除接口。
- `src/domain/diagrams/engine/`
  图表布局、路由、渲染转换主逻辑。
- `frontend/src/components/canvas/Canvas.tsx`
  主画布容器。
- `frontend/src/components/ai/`
  AI 侧栏、消息卡片、预览组件。
- `frontend/src/lib/yjs.ts`
  Excalidraw 与 Yjs 的同步桥接层。

## 环境要求

- 操作系统：Windows 10/11、macOS、Linux
- Python：3.12 及以上
- Node.js：18 及以上
- 推荐 Python 包管理器：`uv`
- 前端包管理器：`npm` 或 `pnpm`

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd SyncCanvas
```

### 2. 安装后端依赖

推荐使用 `uv`：

```bash
uv sync
```

如果你使用 `pip`：

```bash
pip install -r requirements.txt
```

### 3. 检查配置文件

项目首次启动会自动生成：

```text
config/config.toml
```

你至少需要根据自己的模型供应商填写 AI 配置，例如：

- `ai.model_groups`
- `ai.current_model_group`
- 对应模型的 `base_url`
- `api_key`

默认数据库为：

```text
sqlite:///./data/sync_canvas.db
```

默认后端监听地址为：

```text
0.0.0.0:8000
```

### 4. 启动后端

```bash
uv run python main.py
```

启动后：

- API 默认在 `http://localhost:8000`
- WebSocket 默认在 `ws://localhost:8000/ws`

如果前端已构建，后端会直接托管 `frontend/dist`。

### 5. 启动前端开发环境

```bash
cd frontend
npm install
npm run dev
```

默认开发地址：

```text
http://localhost:5173
```

Vite 会将：

- `/api` 代理到后端
- `/ws` 代理到后端 WebSocket

### 6. 构建前端

```bash
cd frontend
npm install
npm run build
```

构建完成后，后端访问根路径 `/` 时会直接返回前端构建产物。

## 常用命令

### 后端

```bash
uv run python main.py
uv run python -m pytest
```

### 前端

```bash
cd frontend
npm run dev
npm run build
npm run test
```

## 数据目录约定

```text
data/
├─ sync_canvas.db   # SQLite 数据库
├─ images/          # 本地上传图片
└─ lib/             # library 文件和索引产物
```

说明：

- 上传图片当前保存在 `data/images/`
- `data/lib/` 用于 library 相关持久化文件
- 当前上传图片到 library 索引的自动联动暂未启用

## 运行机制概览

### 实时协作

画布元素通过 Yjs 文档同步，后端负责房间生命周期、更新持久化、历史回放和版本快照。

### AI 图表主链路

当前受管图表主链路为：

```text
prompt
-> DiagramSpec
-> 后端布局 / 路由 / 渲染
-> Y.Doc diagram maps
-> 前端落板
-> managed reverse-sync
```

### 版本控制

项目为房间级画布维护类似 Git 的快照历史，支持：

- 查看历史
- 创建提交
- 检出历史版本
- 基于历史版本执行回滚

## 当前开发注意事项

- `config/config.toml` 通常包含密钥，不建议提交到仓库。
- 当前工作流以本地单实例画布为主，文档中的“多房间 / 认证”能力不应默认视为产品主入口。
- library 后端代码仍存在，但前端入口和上传联动当前不是主线功能。
- 如果后端提示前端资源未构建，请先在 `frontend/` 下执行 `npm run build` 或直接使用 `npm run dev`。

## README 对应代码状态

本 README 按当前仓库代码状态重写，重点反映以下事实：

- 后端入口为 `main.py`
- 前端为 `frontend/` 下的 React + Vite 项目
- 后端默认使用 SQLite
- 项目已接入 i18n 与主题记忆
- 图片上传落地到 `data/images/`
- library 自动索引当前未作为默认开启能力

## License

本项目使用仓库根目录中的 [LICENSE](LICENSE)。
