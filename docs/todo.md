# SyncCanvas TODO

> 更新时间: 2025-12-11


# 前端主要是美化同时注意遮挡等了现在


# 主要为后端

## 阶段 1：配置系统重构 (P0 - 进行中)

### 1.1 后端配置模型

- [ ] 添加 `APIProviderConfig` 模型
  - 字段: name, base_url, api_key, client_type, max_retry, timeout
  - 位置: `src/config.py`

- [ ] 添加 `ModelEntry` 模型
  - 字段: name, model_identifier, api_provider, model_type, enable_vision, temperature
  - 位置: `src/config.py`

- [ ] 添加 `TaskModelConfig` 模型
  - 字段: model_list, temperature, max_tokens
  - 位置: `src/config.py`

- [ ] 重构 `AIConfig` 使用三层结构
  - api_providers: List[APIProviderConfig]
  - models: List[ModelEntry]
  - model_task_config: Dict[str, TaskModelConfig]

- [ ] 添加旧配置迁移逻辑
  - 在 `_migrate_config()` 中处理旧格式转换

### 1.2 后端配置 API

- [ ] 供应商 CRUD API
  - GET `/config/providers`
  - POST `/config/providers`
  - PUT `/config/providers/{name}`
  - DELETE `/config/providers/{name}`

- [ ] 模型 CRUD API
  - GET `/config/models`
  - POST `/config/models`
  - PUT `/config/models/{name}`
  - DELETE `/config/models/{name}`

- [ ] 任务配置 API
  - GET `/config/task-config`
  - PUT `/config/task-config/{task}`

### 1.3 前端配置 UI

- [ ] 创建供应商管理组件 `ProviderSettings.tsx`
- [ ] 创建模型管理组件 `ModelSettings.tsx`
- [ ] 创建任务配置组件 `TaskConfigSettings.tsx`
- [ ] 重构 `Settings.tsx` 为 Tab 式布局

---

## 阶段 2：LLM 路由器 (P0)

### 2.1 创建 LLMRouter

- [ ] 创建 `src/agent/core/llm_router.py`
  - `get_model_for_task(task: str) -> LLMConfig`
  - `chat_completion(task: str, messages, **kwargs) -> LLMResponse`

- [ ] 实现模型优先级列表
  - 按 model_list 顺序尝试
  - 失败自动切换下一个

- [ ] 实现任务路由逻辑
  - router → 意图分类模型
  - generator → 结构生成模型
  - mutator → 修改操作模型
  - grounding → 指代消解模型

---

## 阶段 3：神经符号架构重构 (P1)

### 3.1 状态注入 (State Hydration)

- [ ] 创建 `summarize_graph(ydoc) -> str`
  - 只保留 ID、Label、Edge 关系
  - 不含坐标，减少 Token

- [ ] 修改 Prompt 模板
  - 注入 `graph_summary` 变量
  - 位置: `src/agent/prompts/`

### 3.2 工具解耦 (逻辑层)

- [ ] 创建逻辑操作工具
  - `add_node(label, type, parent_id) -> Op`
  - `delete_node(node_id) -> Op`
  - `add_edge(from_id, to_id) -> Op`
  - `delete_edge(from_id, to_id) -> Op`
  - 输出操作序列，不含坐标

- [ ] 保留原有工具作为兼容层

### 3.3 几何求解器 (LayoutEngine)

- [ ] 创建 `src/agent/core/layout_engine.py`
  - `apply_operations(ops, graph) -> Graph`
  - `identify_affected_subgraph(ops) -> Set[str]`
  - `compute_layout(graph, affected) -> Graph`

- [ ] 集成布局算法
  - Dagre (层级布局)
  - Force-directed (力导向)

### 3.4 指代消解 (Grounding)

- [ ] 创建 Grounding 模块
  - 解析 "左边那个红框" → node_id
  - 9 宫格空间映射

---

## 阶段 4：Agent 集成 (P1)

### 4.1 BaseAgent 改造

- [ ] 替换 `llm_client` 为 `llm_router`
- [ ] 添加 `task_type` 属性
- [ ] 分离执行管道

### 4.2 PlannerAgent 改造

- [ ] 使用 LLMRouter
- [ ] 实现意图路由
- [ ] 调用 LayoutEngine

### 4.3 CanvaserAgent 改造

- [ ] 使用逻辑操作工具
- [ ] 输出操作序列

---

## 阶段 5：验证与测试 (P2)

- [ ] 配置加载单元测试
- [ ] LLMRouter 集成测试
- [ ] 全流程端到端测试
- [ ] 性能基准测试

---

## 已完成 ✓

- [x] ConfigEditor 通用配置编辑器组件
- [x] WebSocket 连接状态 UI
- [x] 消息路由器 (message_router.py)
- [x] 打字机效果 Hook
- [x] 工具进度组件
- [x] 错误恢复模块 (error_recovery.py)
- [x] Agent 状态机 (state_machine.py)
- [x] Agent 重命名 (Teacher→Planner, Painter→Canvaser)
- [x] 配置自动补全缺失字段

---

## 参考文档

- [AI Agent 架构](./ai_agent.md)
- [功能说明](./features.md)