# SyncCanvas 开发计划

> 更新时间: 2025-12-12

---

## 项目定位

**SyncCanvas: A Reactive Neuro-Symbolic Framework for Human-AI Collaborative Diagramming**

基于 CRDT 的实时协作白板，融合多 LLM 智能体协同编辑。

---

## 当前状态总览

### 已完成

| 模块         | 功能                                 | 文件                   |
| ------------ | ------------------------------------ | ---------------------- |
| ReAct 循环   | Think → Act → Observe 完整实现       | `agent.py`             |
| 房间锁       | 防止同房间多 Agent 冲突              | `RoomLockManager`      |
| 任务委托     | Planner → Canvaser 自动委托          | `planner.py`           |
| 批量创建     | `batch_create_elements` 一次性创建   | `elements.py`          |
| CRDT 持久化  | Commit + Update 的 Git 式存储        | `sync.py`, `ystore.py` |
| 消息路由     | 发布/订阅 + 异步队列                 | `message_router.py`    |
| LLM 故障转移 | 主备自动切换                         | `llm.py`               |
| 配置系统     | Pydantic 模型 + ExtraField UI 元数据 | `config.py`            |
| Prompt 模板  | Jinja2 动态渲染                      | `prompts/`             |
| 状态机       | Agent 执行状态追踪                   | `state_machine.py`     |
| 错误恢复     | 自动重试 + 超时控制                  | `error_recovery.py`    |

### 核心问题

| 问题            | 现状                        | 影响                 |
| --------------- | --------------------------- | -------------------- |
| 同步阻塞        | ReAct 循环完成后才返回      | 用户无法看到中间状态 |
| 无状态注入      | LLM 不知道画布当前状态      | 需要额外工具调用     |
| 坐标由 LLM 输出 | `create_node(x=400, y=180)` | 经常重叠/错位        |
| 无语义冲突检测  | AI 推理期间用户可能修改     | 输出可能基于过时状态 |
| 单一模型        | 所有任务用同一模型          | 无法针对任务优化     |

---

## 论文创新点

### 1. Reactive Blackboard & Event Sourcing

黑板作为事件源，结合 Event Sourcing 存储操作序列，支持时间旅行调试。

### 2. Enhanced Semantic Isolation

预测性冲突检测（基于历史模式）+ 多模态冲突识别 + 分级修复策略。

### 3. Incremental Graph Cognition

增量维护图摘要（Delta Update），延迟更新策略，减少 Token 消耗 70%+。

### 4. Speculative Execution & Rollback

基于用户行为图预测下一步，并行预生成；支持原子化快速回滚。

### 5. Dynamic Spatial Partitioning

基于热力图分析用户活跃区，动态避让 "冷区" 生成内容。

### 6. Multi-Model Ensemble

并行调用多模型（Tier 1/2），拓扑一致性投票融合，提升鲁棒性。

---

## 开发阶段

### 阶段 1: 配置系统重构 (P0)

**目标**: 支持多供应商多模型配置，为 LLM Router 做准备。

#### 1.1 后端配置模型 (增量修改)

- [ ] 添加 `APIProviderConfig` 模型 → `src/config.py`

  ```python
  class APIProviderConfig(BaseModel):
      name: str
      base_url: str
      api_key: str
      max_retry: int = 3
      timeout: float = 60.0
  ```

- [ ] 添加 `ModelEntry` 模型 → `src/config.py`

  ```python
  class ModelEntry(BaseModel):
      name: str
      model_identifier: str
      api_provider: str  # 引用 APIProviderConfig.name
      enable_vision: bool = False
  ```

- [ ] 添加 `TaskModelConfig` 模型 → `src/config.py`

  ```python
  class TaskModelConfig(BaseModel):
      model_list: List[str]  # 优先级列表
      temperature: float = 0.3
      max_tokens: int = 4096
  ```

- [ ] 重构 `AIConfig` → 三层结构

  - `api_providers: List[APIProviderConfig]`
  - `models: List[ModelEntry]`
  - `model_task_config: Dict[str, TaskModelConfig]`

- [ ] 旧配置迁移逻辑

#### 1.2 后端配置 API (新增)

- [ ] `GET/POST/PUT/DELETE /config/providers`
- [ ] `GET/POST/PUT/DELETE /config/models`
- [ ] `GET/PUT /config/task-config`

#### 1.3 前端配置 UI (增量修改)

- [ ] Tab 式 Settings 页面
- [ ] 供应商/模型/任务配置编辑器

---

### 阶段 2: Dynamic LLM Router (P0)

**目标**: 根据任务类型和实时性能选择最优模型。

- [ ] 创建 `src/agent/core/llm_router.py`
  - [ ] 实现 `PerformanceMonitor`: 追踪延迟、错误率
  - [ ] 实现动态路由逻辑: `select_model(task, constraints)`
- [ ] 任务类型与分级定义

  - `Tier 1`: Router / Mutator (Local/Small)
  - `Tier 2`: Generator / Reasoner (Large)

- [ ] 任务分发优化

  - [ ] 实现任务拆分逻辑 (Sub-task Decomposition)
  - [ ] 实现 DAG 依赖调度

- [ ] 修改 `BaseAgent` 使用 `LLMRouter` 替代 `LLMClient`

---

### 阶段 3: 增量状态注入 (P1)

**目标**: 高效让 LLM 了解画布当前状态。

#### 3.1 图摘要生成 (新增)

- [ ] 创建 `src/agent/core/graph_summary.py`

  - [ ] `summarize_graph(ydoc)`: 全量摘要
  - [ ] `get_delta_summary(prev, curr)`: 差分摘要 **(Enhanced)**

- [ ] 修改 Prompt 模板注入 `{{delta_summary}}`

#### 3.2 增量图认知 (创新点 3)

- [ ] 创建 `src/agent/core/graph_cognition.py`
  - [ ] 监听 Yjs 变更事件
  - [ ] 实现 **延迟更新 (Lazy Update)** 策略
  - [ ] 实现 **增量推送 (Incremental Push)** 到前端

---

### 阶段 4: 拓扑与几何解耦 & 布局增强 (P1)

**目标**: LLM 只输出逻辑，算法计算坐标，保证布局稳定。

#### 4.1 逻辑操作工具 (新增)

- [ ] 创建 `src/agent/tools/logical_ops.py`
  - 输出操作序列 `List[Op]`，无坐标
  - 支持 `add_node`, `delete_edge` 等原子操作

#### 4.2 LayoutEngine (新增)

- [ ] 创建 `src/agent/core/layout_engine.py`
  - [ ] 集成 **Force-directed** (力导向) 算法
  - [ ] 实现 **Cognitive Map Preservation** (认知地图保持): 最小化节点移动
  - [ ] 实现 **Dynamic Spatial Partitioning**:
    - 集成热力图分析 (User Heatmap)
    - 动态计算 "冷区" (Cold Zone)

#### 4.3 多模型集成 (Enhanced)

- [ ] 创建 `src/agent/core/ensemble.py`
  - [ ] 实现 **Parallel Execution**: 并行调用生成与逻辑模型
  - [ ] 实现 **Voting Mechanism**: 拓扑一致性检查与融合

---

### 阶段 5: 流式响应 & 异步处理 (P2)

**目标**: 边生成边渲染，提升大规模并发性能。

- [ ] LLM 调用启用 `stream=True`
- [ ] 流式 JSON 解析 (识别完整 Op 后立即执行)
- [ ] **Async Task Queue**:

  - [ ] 引入 `asyncio.Queue` (或 Celery) 处理耗时任务 (布局/生图)
  - [ ] 实现任务优先级调度

- [ ] WebSocket 实时推送
  - `element:preview` (乐观更新)
  - `element:confirm` (后端确认)

---

### 阶段 6: 增强语义冲突检测 (P2)

**目标**: 智能防止冲突，多模态检测。

- [ ] 创建 `src/agent/core/semantic_transaction.py`
  - [ ] 实现 **Predictive Conflict Detection**: 基于历史模式预测
  - [ ] 实现 **Multi-modal Detection**: 语义 + 空间 + 属性
- [ ] 冲突解决策略
  - [ ] Auto-fix (力导向弹开)
  - [ ] Re-reason (重推理)
  - [ ] Rollback (回滚)

---

### 阶段 7: 投机执行 & 回滚 (P3)

**目标**: 预测用户下一步，降低感知延迟。

- [ ] 创建 `src/agent/core/speculative.py`
  - [ ] 建立 `UserActionGraph` 进行行为预测
  - [ ] 实现 `pending` 状态管理 (前端虚线显示)
- [ ] 回滚机制
  - [ ] 实现 **Fast Rollback**: 原子化撤销未确认的 speculation

---

### 阶段 8: 数据存储优化 (P3)

**目标**: 提升数据查询与同步效率。

- [ ] **Event Sourcing**:

  - [ ] 设计操作日志存储 (`LogStore`)
  - [ ] 支持基于日志的时间旅行恢复

- [ ] 增量数据库优化
  - [ ] 优化 `Commit`/`Update` 存储结构

---

### 阶段 9: 验证与测试

- [ ] 配置系统单元测试
- [ ] LLMRouter 动态路由测试
- [ ] 增量摘要准确性测试
- [ ] 布局稳定性测试 (偏移量指标)
- [ ] 冲突预测准确率测试
- [ ] 端到端性能基准 (E2E Latency)

---

## 参考

- [AI Agent 架构](./ai_agent.md)
- [功能说明](./features.md)
- [项目分析报告](walkthrough.md)
