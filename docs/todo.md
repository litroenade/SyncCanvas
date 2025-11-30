# SyncCanvas TODO

## 已完成

- [x] 基础绘图工具 (矩形、圆形、菱形、箭头、线条、画笔、文本)
- [x] 实时协作同步 (Yjs + pycrdt-websocket)
- [x] 用户认证 (JWT)
- [x] 游客模式
- [x] 图层管理
- [x] 导出 PNG
- [x] 暗色/亮色主题
- [x] 数据持久化 (统一 SQLModel 数据库)
- [x] Git 式存储 (Snapshot + Update)
- [x] AI 生成图形 (基础)
- [x] 房间 CRUD API
- [x] 房间列表页面
- [x] 创建房间 (支持密码保护)
- [x] 数据库模型 (User, Room, RoomMember, Stroke, Snapshot, Update)
- [x] Docker 配置 (Dockerfile + docker-compose.yml)
- [x] features.md - 功能说明
- [x] todo.md - 待办事项

## 进行中

### 核心功能
- [ ] 在线用户显示 (Awareness)
- [ ] 房间成员管理 UI
- [ ] 邀请链接生成

### 编辑器增强
- [ ] 组合/取消组合图形 (Ctrl+G / Ctrl+Shift+G)
- [ ] 复制/粘贴 (Ctrl+C/V/D)
- [ ] 智能连接线 (图形间自动吸附)
- [ ] 对齐工具 (左对齐、居中、分布)
- [ ] 锁定图层

## 待实现

### 协作功能
- [ ] 评论/批注功能
- [ ] @提及用户
- [ ] 评论通知

### MCP Server
- [ ] MCP Server 实现
- [ ] Resources: 读取白板内容
- [ ] Tools: 操作白板 (添加/更新/删除图形)
- [ ] Prompts: 预设模板 (流程图、思维导图)
- [ ] AI Agent 集成测试

### 导入导出
- [ ] 导出 SVG
- [ ] 导出 PDF
- [ ] 导入 Excalidraw 格式
- [ ] 导入图片 OCR 提取文字

### 高级功能
- [ ] 历史版本回溯
- [ ] 模板库 (流程图、思维导图、ER图)
- [ ] 插件系统
- [ ] 移动端适配

## 技术债务

- [ ] 统一文件命名规范 (useCanvasStore.ts vs use_websocket.ts)
- [ ] 补充单元测试
- [ ] 补充 E2E 测试
- [ ] 性能优化 (大量图形时的渲染)
- [ ] 错误处理优化

## 已知问题

- [ ] 文本编辑时快捷键冲突
- [ ] 移动端触摸事件优化
- [ ] 缩放时网格线条粗细不一致

## 文档

- [x] features.md - 功能说明
- [x] todo.md - 待办事项
- [ ] deployment.md - 部署指南
- [ ] api.md - API 文档
- [ ] contributing.md - 贡献指南
