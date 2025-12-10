# SyncCanvas TODO

> 更新时间: 2025-12-10

## 优先级 P0 - 必须完成

### 1. 集成新增的 Agent 模块
- [ ] 将 `error_recovery.py` 集成到 `PlannerAgent` 和 `CanvaserAgent`
- [ ] 将 `state_machine.py` 集成到 Agent 执行流程
- [ ] 统一错误处理和重试逻辑

### 2. 前端组件集成 ✓
- [x] 在 Canvas 页面集成 `ConnectionStatus` 组件显示连接状态 (通过 renderTopRightUI)
- [x] 在 AI 对话面板集成 `ToolProgress` 组件显示工具执行进度
- [x] 集成 `useTypingEffect` 实现 AI 回复打字机效果

### 3. 后端 WebSocket 升级
- [ ] 将 `message_router` 集成到 AI WebSocket 端点
- [ ] 实现消息订阅/取消订阅功能

---

## 优先级 P1 - 重要

### 4. 配置系统完善
- [ ] 后端实现 `PUT /config/{group}/{key}` 接口
- [ ] 前端 ConfigEditor 对接后端保存 API
- [ ] 添加配置变更验证

### 5. AI Agent 优化
- [ ] 优化 CanvaserAgent 的坐标计算逻辑
- [ ] 增加流程图自动布局算法
- [ ] 支持更多图表类型 (时序图、类图)

### 6. 用户体验
- [ ] 添加画布加载进度条
- [ ] 优化移动端 FAB 交互
- [ ] 添加键盘快捷键支持

---

## 优先级 P2 - 待定

### 7. 历史和版本控制
- [ ] 完善画布历史回退功能
- [ ] 添加版本对比视图
- [ ] 优化 commit 存储效率

### 8. 协作功能
- [ ] 实现用户光标同步
- [ ] 添加在线用户头像显示
- [ ] 支持评论和标注

### 9. 导出和分享
- [ ] 支持导出为 PNG/SVG
- [ ] 支持导出为 PDF
- [ ] 生成分享链接

---

## 已完成

- [x] ConfigEditor 通用配置编辑器组件
- [x] WebSocket 连接状态 UI (ConnectionStatus)
- [x] 消息路由器 (message_router.py)
- [x] 打字机效果 Hook (useTypingEffect)
- [x] 工具进度组件 (ToolProgress)
- [x] 错误恢复模块 (error_recovery.py)
- [x] Agent 状态机 (state_machine.py)
- [x] Agent 重命名 (Teacher→Planner, Painter→Canvaser)