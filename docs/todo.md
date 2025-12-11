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

### 1. Reactive Blackboard Architecture

黑板作为事件源，发布/订阅而非轮询。

### 2. Semantic Snapshot Isolation

AI 提交时检测语义冲突，自动修复或请求重推理。

### 3. Incremental Graph Cognition

增量维护图摘要，减少 Token 消耗 60%+。

### 4. Speculative Execution

预测用户下一步，预生成响应，命中则零延迟。

### 5. Spatial Partitioning

画布分区，AI 自动选择空闲区域，避免冲突。

### 6. Multi-Model Ensemble

多模型并行生成，投票融合结果。

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

### 阶段 2: LLM Router (P0)

**目标**: 根据任务类型选择最优模型。

- [ ] 创建 `src/agent/core/llm_router.py`

  ```python
  class LLMRouter:
      def get_model_for_task(self, task: str) -> LLMConfig
      async def chat_completion(self, task: str, messages, **kwargs) -> LLMResponse
  ```

- [ ] 任务类型定义

  - `router` → 意图分类 (gpt-4o-mini)
  - `generator` → 结构生成 (deepseek-v3)
  - `mutator` → 增量修改 (qwen-14b)
  - `grounding` → 指代消解 (gpt-4o-mini)

- [ ] 模型优先级列表 + 自动故障转移

- [ ] 修改 `BaseAgent` 使用 `LLMRouter` 替代 `LLMClient`

---

### 阶段 3: 状态注入 (P1)

**目标**: 让 LLM 了解画布当前状态。

#### 3.1 图摘要生成 (新增)

- [ ] 创建 `src/agent/core/graph_summary.py`

  ```python
  def summarize_graph(ydoc) -> str:
      """生成轻量拓扑描述 (无坐标)"""
      # 输出: "Nodes: [A(start), B(process)], Edges: [A→B]"
  ```

- [ ] 修改 Prompt 模板注入 `{{graph_summary}}`

#### 3.2 增量图认知 (创新点 3)

- [ ] 创建 `src/agent/core/graph_cognition.py`
  - 监听 Yjs 变更事件
  - 增量更新摘要缓存
  - 缓存失效策略

---

### 阶段 4: 拓扑与几何解耦 (P1)

**目标**: LLM 只输出逻辑，算法计算坐标。

#### 4.1 逻辑操作工具 (新增)

- [ ] 创建 `src/agent/tools/logical_ops.py`
  ```python
  def add_node(label, type, parent_id) -> Op
  def delete_node(node_id) -> Op
  def add_edge(from_id, to_id) -> Op
  def delete_edge(from_id, to_id) -> Op
  ```
  - 输出操作序列 `List[Op]`，无坐标

#### 4.2 LayoutEngine (新增)

- [ ] 创建 `src/agent/core/layout_engine.py`

  ```python
  class LayoutEngine:
      def apply_operations(self, ops, graph) -> Graph
      def identify_affected_subgraph(self, ops) -> Set[str]
      def compute_layout(self, graph, affected) -> Graph
  ```

- [ ] 集成布局算法
  - Dagre (层级布局)
  - Force-directed (力导向)

#### 4.3 保留兼容

- [ ] 原有工具 (`create_flowchart_node` 等) 作为降级路径
- [ ] 简单任务走旧路径，复杂任务走新管道

---

### 阶段 5: 流式响应 (P2)

**目标**: 边生成边渲染，提升体验。

- [ ] LLM 调用启用 `stream=True`
- [ ] 流式 JSON 解析 (识别完整 Op 后立即执行)
- [ ] WebSocket 实时推送
  - `element:preview` (乐观更新)
  - `element:confirm` (后端确认)
- [ ] 前端乐观更新 + 修正动画

---

### 阶段 6: 语义冲突检测 (P2)

**目标**: 防止 AI 输出基于过时状态。

- [ ] 创建 `src/agent/core/semantic_transaction.py`

  ```python
  class SemanticTransaction:
      def __init__(self, snapshot_version)
      def commit(self, current_state) -> CommitResult
      def detect_semantic_conflicts(self, state) -> List[Conflict]
      def auto_repair(self, conflicts) -> Optional[List[Op]]
  ```

- [ ] 冲突类型: 引用失效、空间冲突、语义矛盾
- [ ] 修复策略: 自动修复 → LLM 重推理 → 用户裁决

---

### 阶段 7: 投机执行 (P3)

**目标**: 预测用户下一步，降低感知延迟。

- [ ] 创建 `src/agent/core/speculative.py`
- [ ] 预测策略 (基于操作序列/图结构)
- [ ] 并行预生成候选响应
- [ ] 命中/回滚机制

---

### 阶段 8: 空间分区 (P3)

**目标**: 避免 AI 与用户操作冲突。

- [ ] 画布 9 宫格分区
- [ ] AI 自动选择空闲区域
- [ ] 用户进入 AI 区域 → AI 暂停/迁移
- [ ] 跨区连接协调协议

---

### 阶段 9: 多模型投票 (P3)

**目标**: 提升输出质量和一致性。

- [ ] 并行调用多模型
- [ ] 结果相似度比对
- [ ] 投票/置信度融合
- [ ] 冲突展示给用户选择

---

### 阶段 10: 验证与测试

- [ ] 配置系统单元测试
- [ ] LLMRouter 集成测试
- [ ] 图摘要准确性测试
- [ ] 布局算法效果测试
- [ ] 语义冲突场景测试
- [ ] 端到端性能基准

---

## 参考

- [AI Agent 架构](./ai_agent.md)
- [功能说明](./features.md)
- [项目分析报告](walkthrough.md)
