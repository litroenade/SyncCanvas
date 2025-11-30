# SyncCanvas 功能文档

## 项目概述

SyncCanvas 是一个基于 CRDT 的实时协作白板系统，支持多用户同时编辑、实时同步、持久化存储等功能。

## 技术栈

### 后端
- **Python 3.12** + **FastAPI** - Web 框架
- **pycrdt-websocket** - Yjs 兼容的 CRDT WebSocket 服务
- **SQLModel** - ORM，基于 SQLAlchemy + Pydantic
- **SQLite** - 数据库（可替换为 PostgreSQL）
- **JWT** - 用户认证

### 前端
- **React 18** + **TypeScript** - UI 框架
- **Vite 6** - 构建工具
- **Konva.js** - Canvas 绑定库
- **Yjs** + **y-websocket** - CRDT 实时协作
- **Zustand** - 状态管理
- **Tailwind CSS 4** - 样式

## 核心功能

### 1. 实时协作 (CRDT)

基于 Yjs/pycrdt 实现的无冲突复制数据类型：
- 多用户同时编辑，自动合并冲突
- 低延迟实时同步
- 支持离线编辑，重连后自动同步

### 2. 数据持久化

#### 统一数据库设计

所有数据存储在单一 SQLite 数据库 (`data/sync_canvas.db`)：

```
┌─────────────────────────────────────────────────────────────────┐
│                      sync_canvas.db                              │
├─────────────────────────────────────────────────────────────────┤
│  User        - 用户信息、认证                                    │
│  Room        - 房间配置、访问控制                                │
│  RoomMember  - 房间成员关系                                      │
│  Stroke      - 图形数据（JSON）                                  │
│  Snapshot    - Yjs 文档完整快照（二进制）                        │
│  Update      - Yjs 增量更新（二进制）                            │
└─────────────────────────────────────────────────────────────────┘
```

#### Git 式存储策略

类似 Git 的设计思路：
- **Snapshot** = Git Commit（完整状态快照）
- **Update** = Git Diff（增量变更）
- **压缩** = Git GC（合并历史）

工作流程：
1. 用户操作产生 Yjs Update → 写入 `update` 表
2. Update 数量超过阈值（默认 100）→ 触发压缩
3. 压缩：所有 Update 合并为一个 Snapshot
4. 删除旧的 Update 和 Snapshot

### 3. 房间管理

- 创建/删除房间
- 房间密码保护（SHA-256 + Salt）
- 公开/私有房间
- 最大用户数限制
- 成员角色管理（owner/editor/viewer）

### 4. 用户认证

- 用户名 + 服务端密钥认证
- JWT Token
- 游客访问（无需登录）

### 5. 绘图工具

| 工具 | 说明 |
|------|------|
| 选择 | 选择、移动、缩放图形 |
| 矩形 | 绘制矩形 |
| 圆形 | 绘制圆形/椭圆 |
| 箭头 | 绘制箭头线 |
| 直线 | 绘制直线 |
| 自由绘制 | 手绘笔画 |
| 文本 | 添加文本 |
| 图片 | 插入图片 |

### 6. 画布功能

- 无限画布
- 缩放/平移
- 网格显示
- 图层管理
- 撤销/重做
- 导出 PNG/SVG/JSON

## 目录结构

```
SyncCanvas/
├── main.py              # 应用入口
├── config.toml          # 配置文件
├── data/                # 数据目录（git 忽略内容）
│   ├── sync_canvas.db   # SQLite 数据库
│   ├── settings.json    # 运行时设置（含 secret_key）
│   └── images/          # 上传的图片
├── src/
│   ├── config.py        # 配置加载
│   ├── logger.py        # 日志配置
│   ├── auth/            # 认证模块
│   ├── db/              # 数据库模块
│   │   ├── models.py    # 数据模型
│   │   ├── crud.py      # CRUD 操作
│   │   ├── database.py  # 数据库连接
│   │   └── ystore.py    # Yjs 持久化存储
│   ├── routers/         # API 路由
│   └── ws/              # WebSocket 同步
└── frontend/            # React 前端
```

## API 端点

### 认证
- `POST /auth/token` - 登录获取 Token

### 房间
- `GET /rooms` - 获取房间列表
- `POST /rooms` - 创建房间
- `GET /rooms/{room_id}` - 获取房间详情
- `DELETE /rooms/{room_id}` - 删除房间
- `POST /rooms/{room_id}/join` - 加入房间
- `POST /rooms/{room_id}/leave` - 离开房间

### WebSocket
- `WS /ws/{room_id}` - Yjs 同步连接

### 其他
- `POST /ai/generate` - AI 生成图形
- `POST /upload/image` - 上传图片
