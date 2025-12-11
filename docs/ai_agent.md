# SyncCanvas AI Agent 架构文档

> 更新时间: 2025-12-12

---

## 一、项目定位

**SyncCanvas: A Reactive Neuro-Symbolic Framework for Human-AI Collaborative Diagramming**

实时协作白板 + 多 LLM 智能体协同编辑 + 神经符号架构。

---

## 二、架构演进

### 现有架构 (Current)

```
User Input
    ↓
PlannerAgent ──────────────────────────────────────────────────────
    │                                                              │
    │ 关键词匹配: "画/流程图/架构图"?                                 │
    ↓                                                              │
    ├── YES → CanvaserAgent                                        │
    │              ↓                                               │
    │         ReAct Loop ────────────────────────────────          │
    │              │                                   │           │
    │         ┌────┴────┐                              │           │
    │         │         │                              │           │
    │      THINK     ACT (含坐标)                      │           │
    │         │         │                              │           │
    │         │    create_flowchart_node(x=400, y=180) │           │
    │         │         ↓                              │           │
    │         │    Yjs 写入 → 广播                      │           │
    │         │         │                              │           │
    │         └────────→ OBSERVE ──────────────────────            │
    │                                                              │
    └── NO → 自己处理 (ReAct Loop) ────────────────────────────────
```

**特点:**

- LLM 直接输出坐标 → 不可靠
- 无状态注入 → LLM 不知道画布状态
- 同步阻塞 → 用户等待全部完成
- 单一模型 → 无法针对任务优化

### 目标架构 (Target)

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: State Hydration (状态注入)                              │
│   GraphCognition.get_summary() → 轻量拓扑描述 (无坐标)            │
│   构建上下文: {指令, 摘要, 历史, 用户关注区}                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Intent Routing (意图路由)                               │
│   LLMRouter.route(task="router") → create / modify / query      │
│   分发给对应 Agent + 启动投机预测                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Logical Reasoning (逻辑推理) [Neuro]                    │
│   Generator: add_node("2FA", type="process", after="Login")     │
│   输出逻辑操作序列 → 无坐标                                        │
│   Grounding: "左边那个红框" → node_id                             │
│   SemanticTransaction 开始                                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Geometric Solving (几何求解) [Symbolic]                 │
│   LayoutEngine.compute_layout(ops, affected_subgraph)           │
│   → 确定性坐标计算                                                │
│   空间分区检查 → 避免与用户冲突                                     │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Commit & Broadcast (提交广播)                           │
│   SemanticTransaction.commit() → 冲突检测                        │
│   ├── SUCCESS → CRDT 写入 + WebSocket 广播                       │
│   ├── REPAIRED → 自动修复后提交                                   │
│   └── CONFLICT → 回滚 / 重推理 / 用户裁决                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件

### 3.1 已实现

| 组件                       | 文件                | 功能                   |
| -------------------------- | ------------------- | ---------------------- |
| **BaseAgent**              | `agent.py`          | ReAct 循环、重试、超时 |
| **RoomLockManager**        | `agent.py`          | 房间级并发锁           |
| **PlannerAgent**           | `planner.py`        | 意图识别、任务委托     |
| **CanvaserAgent**          | `canvaser.py`       | 批量创建、布局计算     |
| **LLMClient**              | `llm.py`            | 主备故障转移           |
| **ToolRegistry**           | `tools.py`          | OpenAI Schema 生成     |
| **WebSocketMessageRouter** | `message_router.py` | 发布/订阅              |

### 3.2 待实现

| 组件                    | 位置                            | 功能            |
| ----------------------- | ------------------------------- | --------------- |
| **LLMRouter**           | `agent/core/llm_router.py`      | 任务 → 模型映射 |
| **GraphCognition**      | `agent/core/graph_cognition.py` | 增量图摘要缓存  |
| **LayoutEngine**        | `agent/core/layout_engine.py`   | 几何求解器      |
| **SemanticTransaction** | `core/semantic_transaction.py`  | 语义冲突检测    |
| **SpeculativeEngine**   | `agent/core/speculative.py`     | 投机执行        |
| **RouterAgent**         | `agent/agents/router.py`        | 意图分类        |
| **GeneratorAgent**      | `agent/agents/generator.py`     | 结构生成        |
| **MutatorAgent**        | `agent/agents/mutator.py`       | 增量修改        |

---

## 四、论文创新点

### 创新点 1: Reactive Blackboard

**问题**: 传统黑板模式依赖轮询。

**解决**: 事件驱动，发布/订阅响应式协作。

```
┌──────────────────────────────────────────┐
│        Reactive Blackboard Core          │
│  Canvas State (Yjs) + Event Stream       │
└──────────────────────────────────────────┘
         │ Pub/Sub │
    ┌────┴────┬────┴────┬────┴────┐
    ▼         ▼         ▼         ▼
  User     Router   Generator  Layout
```

### 创新点 2: Semantic Snapshot Isolation

**问题**: AI 推理期间用户修改画布 → 语义冲突。

**解决**: 提交时检测语义冲突，自动修复或重推理。

```python
class SemanticTransaction:
    def commit(self, current_state) -> CommitResult:
        conflicts = self.detect_semantic_conflicts(current_state)
        if conflicts:
            repaired = self.auto_repair(conflicts)
            return REPAIRED if repaired else NEEDS_RETRY
        return SUCCESS
```

### 创新点 3: Incremental Graph Cognition

**问题**: 每次全量序列化画布浪费 Token。

**解决**: 增量维护图摘要，变更时 Δ 更新。

```python
class GraphCognition:
    topology: str           # "A→B→C"
    spatial_index: Dict     # 9宫格索引
    semantic_clusters: List # 语义聚类

    def on_element_changed(self, delta):
        # 增量更新，不重算全部
```

### 创新点 4: Topology-Geometry Decoupling

**问题**: LLM 输出坐标不可靠。

**解决**: LLM 只输出逻辑，LayoutEngine 计算坐标。

| 现状                        | 目标                                 |
| --------------------------- | ------------------------------------ |
| `create_node(x=400, y=180)` | `add_node(label="A", after="Login")` |
| 坐标经常重叠                | 确定性布局算法                       |

### 创新点 5: Speculative Execution

**问题**: LLM 推理延迟高。

**解决**: 预测用户下一步，预生成响应。

```
用户: "画一个登录流程"
├── 主分支: 生成流程图
├── 预测分支1: 预生成 "添加验证步骤"
└── 预测分支2: 预生成 "连接数据库"

用户: "加个验证" → 命中预测1 → 延迟 < 100ms
```

### 创新点 6: Spatial Partitioning

**问题**: AI 和用户同时操作同一区域 → 冲突。

**解决**: 画布分区，AI 自动选择空闲区域。

```
┌─────────┬─────────┬─────────┐
│ [User]  │ [AI]    │ [Idle]  │
├─────────┼─────────┼─────────┤
│ [Idle]  │ [User]  │ [AI]    │
└─────────┴─────────┴─────────┘
```

---

## 五、多模型协作

### 任务类型 → 模型映射

| 任务        | 特点     | 推荐模型    |
| ----------- | -------- | ----------- |
| `router`    | 快速分类 | gpt-4o-mini |
| `generator` | 复杂推理 | deepseek-v3 |
| `mutator`   | 快速响应 | qwen-14b    |
| `grounding` | 空间推理 | gpt-4o-mini |

### 配置示例

```toml
[model_task_config.router]
model_list = ["gpt-4o-mini", "qwen-7b"]
temperature = 0.1

[model_task_config.generator]
model_list = ["deepseek-v3", "qwen-72b"]
temperature = 0.3
```

---

## 六、执行流程示例

**用户输入**: "在 Login 和 Home 之间加一个 2FA 验证"

### Phase 1 (状态注入)

```json
{
  "instruction": "Insert 2FA between Login and Home",
  "graph_summary": "Nodes: [Login(n1), Home(n2)], Edges: [n1→n2]"
}
```

### Phase 3 (逻辑推理)

```json
[
  { "op": "delete_edge", "src": "n1", "tgt": "n2" },
  { "op": "add_node", "id": "n3", "label": "2FA", "type": "process" },
  { "op": "add_edge", "src": "n1", "tgt": "n3" },
  { "op": "add_edge", "src": "n3", "tgt": "n2" }
]
```

### Phase 4 (几何求解)

```json
{
  "layout": [
    { "id": "n3", "x": 400, "y": 255 },
    { "id": "n2", "x": 400, "y": 410 }
  ]
}
```

### Phase 5 (提交)

- 冲突检测 → 无冲突
- CRDT 写入 → 广播

---

## 七、性能目标

| 指标         | 目标    |
| ------------ | ------- |
| 意图路由延迟 | < 200ms |
| 首个 Op 输出 | < 500ms |
| 布局计算     | < 100ms |
| 同步延迟     | < 50ms  |
| Token 节省   | > 60%   |
| 投机命中率   | > 30%   |

---

## 八、相关文件

| 文档                      | 用途         |
| ------------------------- | ------------ |
| [开发计划](./todo.md)     | 详细任务列表 |
| [功能说明](./features.md) | 用户功能文档 |
