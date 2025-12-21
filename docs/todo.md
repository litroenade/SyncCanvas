# SyncCanvas 开发计划

> 更新时间: 2025-12-21

---

## 项目概述

**SyncCanvas**: 基于 CRDT 的实时协作白板 + AI 智能绘图

核心特性:

- 🎨 Excalidraw 风格无限画布
- 🤖 AI Agent 自动绘制流程图/架构图
- 🔄 Yjs CRDT 实时多人协作
- 📚 素材库 + 向量语义搜索

---

## 已完成功能

### 后端

| 模块        | 功能                              | 位置                     |
| ----------- | --------------------------------- | ------------------------ |
| ReAct Agent | Think → Act → Observe 循环        | `agent/core/base.py`     |
| 工具注册    | 装饰器自动注册 + Schema           | `agent/core/registry.py` |
| LLM 客户端  | OpenAI 兼容 + 故障转移            | `agent/core/llm.py`      |
| 绘图工具    | batch_create, flowchart, elements | `agent/tools/`           |
| 素材库服务  | SQLite + FAISS 向量搜索           | `services/library.py`    |
| 布局引擎    | 力导向自动布局                    | `agent/canvas/layout.py` |
| CRDT 持久化 | Commit/Update Git 式存储          | `db/ystore.py`           |
| 配置系统    | Pydantic + 模型组管理             | `config.py`              |

### 前端

| 模块     | 功能               | 位置                                  |
| -------- | ------------------ | ------------------------------------- |
| 画布组件 | Excalidraw 集成    | `components/canvas/Canvas.tsx`        |
| AI 助手  | 对话 + 流式响应    | `components/canvas/AIAssistant.tsx`   |
| 版本历史 | Git 式提交记录     | `components/canvas/HistoryPanel.tsx`  |
| 设置面板 | 模型配置 UI        | `components/canvas/SettingsPanel.tsx` |
| Yjs 同步 | WebSocket 实时同步 | `lib/yjs.ts`                          |

---

## 待开发功能

### P0 - 核心体验

#### 1. AI 绘图稳定性

- [ ] 修复 Y.Map 元素同步问题 (已有方案待验证)
- [ ] 优化坐标计算避免元素重叠
- [ ] 添加元素创建失败重试机制

#### 2. 素材库 UI

**Excalidraw 自带:**

- [x] 素材库浏览面板 (工具栏左侧 "库" 按钮)
- [x] 素材预览卡片 + 拖拽插入
- [x] 导入本地 .excalidrawlib 文件

**需扩展 (后端 RAG 搜索):**

- [ ] 连接后端 FAISS 语义搜索
- [ ] 前端搜索结果展示

#### 3. AI 交互优化

- [ ] 显示 AI 执行步骤 (Think/Act/Observe)
- [ ] 工具调用进度可视化
- [ ] 生成中元素虚线预览

### P1 - 增强功能

#### 4. 配置系统增强

- [ ] 多供应商配置 (OpenAI/Claude/本地)
- [ ] 任务级模型分配 (小模型路由/大模型生成)
- [ ] API Provider 健康检查

#### 5. 增量状态注入

- [ ] 画布状态摘要注入 Prompt
- [ ] 差分更新 (Delta Summary)
- [ ] 减少 Token 消耗

#### 6. 流式响应

- [ ] LLM stream=True
- [ ] 逐步解析 JSON 操作
- [ ] WebSocket 推送中间状态

### P2 - 进阶功能

#### 7. 冲突检测与解决

- [ ] AI 推理期间锁定区域
- [ ] 冲突预测 (基于历史模式)
- [ ] 自动修复/回滚策略

#### 8. 投机执行

- [ ] 用户行为预测
- [ ] 预生成缓存
- [ ] 快速回滚

#### 9. 多模型集成

- [ ] 并行调用多模型
- [ ] 拓扑一致性投票
- [ ] 结果融合

---

## 技术债务

- [ ] 清理未使用的 pipeline/ 目录代码
- [ ] 统一错误处理格式
- [ ] 添加单元测试覆盖
- [ ] 补充 API 文档

---

## 文档

- [AI Agent 架构](./ai_agent.md)
- [功能说明](./features.md)
- [项目分析报告](walkthrough.md)
