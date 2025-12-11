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

### 目标架构 (Target)

引入**动态路由**、**增量认知**与**投机执行**的增强型架构：

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Incremental State Hydration (增量状态注入)              │
│   GraphCognition.get_delta_summary() → 仅变更部分的语义描述       │
│   Context: {Instruction, DeltaSummary, History, UserFocus(Heatmap)}|
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Dynamic Intent Routing (动态意图路由)                   │
│   LLMRouter: 基于 [模型延迟, 错误率] 动态打分                    │
│   Route: Task → (Model A + Model B) [Ensemble/Parallel]         │
│   分发策略: Router / Generator / Mutator / Grounding            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Logical Reasoning (逻辑推理) [Neuro, Parallel]          │
│   Generator (Model A): add_node("2FA", type="process")          │
│   Mutator (Model B): optimize_flow()                            │
│   → Voting/Fusion (多模型投票融合) → 统一逻辑 Op 序列             │
│   → Speculative Engine: 预测后续 Op (如 "添加 Edge")             │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Stable Geometric Solving (布局求解) [Symbolic]          │
│   LayoutEngine: Force-directed + Constraints                    │
│   认知地图保持: 最小化移动，保留用户习惯布局                       │
│   Dynamic Spatial Partitioning: 基于热力图避让用户活跃区          │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Semantic Transaction (语义事务)                         │
│   Conflict Detection: 预测性冲突 (根据历史模式) + 即时冲突         │
│   Auto Repair: 自动调整 > 重推理 > 回滚                          │
│   Commit: Event Sourcing Log + CRDT Update                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件

### 3.1 已实现组件

| 组件                       | 文件                | 功能                   |
| -------------------------- | ------------------- | ---------------------- |
| **BaseAgent**              | `agent.py`          | ReAct 循环、重试、超时 |
| **RoomLockManager**        | `agent.py`          | 房间级并发锁           |
| **PlannerAgent**           | `planner.py`        | 意图识别、任务委托     |
| **CanvaserAgent**          | `canvaser.py`       | 批量创建、布局计算     |
| **LLMClient**              | `llm.py`            | 主备故障转移           |
| **WebSocketMessageRouter** | `message_router.py` | 发布/订阅              |

### 3.2 待实现增强组件

| 组件                  | 模块                  | 增强功能                         |
| --------------------- | --------------------- | -------------------------------- |
| **DynamicLLMRouter**  | `core/router.py`      | 性能评分、动态权重、任务分级调度 |
| **GraphCognition**    | `core/cognition.py`   | 增量更新、图摘要缓存、Diff 计算  |
| **LayoutEngine**      | `core/layout.py`      | 力导向、认知地图保持、增量布局   |
| **SemanticMonitor**   | `core/semantic.py`    | 预测性冲突检测、多模态冲突识别   |
| **SpeculativeEngine** | `core/speculative.py` | 历史行为预测、推测执行、回滚机制 |
| **EnsembleManager**   | `core/ensemble.py`    | 多模型结果投票、加权融合         |

---

## 四、深度增强设计 (Deep Enhancements)

### 1. 动态任务路由与分发 (Dynamic Routing)

**优化目标**: 解决静态路由灵活性不足的问题，提升系统吞吐量。

- **性能反馈循环**: 维护每个模型的实时指标（延迟 p99、Token 吞吐、错误率）。路由时不仅看任务类型，还结合模型当前负载和健康度。
  - _Code Example_: `router.select_model(task_type="gen_flow", constraints={max_latency: 500ms})`
- **任务分级 (Tiered Routing)**:
  - `Tier 1 (Real-time)`: 简单修改、位置调整 → `Llama-3-8B / Qwen-14B` (Local/Fast API)
  - `Tier 2 (Reasoning)`: 复杂生成、逻辑纠错 → `GPT-4o / DeepSeek-V3`
- **细粒度拆分**: 将 "画一个电商下单流程" 拆解为 `[生成节点列表]` (并行) + `[生成连接关系]` (串行依赖)，通过 DAG 调度执行。

### 2. 多模型集成 (Multi-Model Ensemble)

**优化目标**: 提升复杂任务的鲁棒性，减少单一模型的幻觉。

- **并行执行 (Parallel Execution)**: 对于关键决策（如架构设计），同时请求 Model A (Creativity) 和 Model B (Logic)。
- **投票融合 (Voting Mechanism)**:
  - 拓扑一致性检查：如果 A 和 B 生成的图结构拓扑距离 (Graph Edit Distance) 小于阈值，则自动合并属性。
  - 分歧仲裁：差异过大时，引入 Model C (Arbiter) 或降级请求用户确认。

### 3. 增量图认知 (Incremental Graph Cognition)

**优化目标**: 降低 Token 消耗，提升长窗口对话的响应速度。

- **差分摘要 (Delta Summarization)**: 仅在 `Context` 中注入自上次交互以来的变更 (`Last_Turn_State` vs `Current_State`)。
- **延迟更新策略 (Lazy Update)**: 用户频繁拖拽时不触发重算，静止 500ms 后触发 `GraphCognition.update()`。
- **增量推送**: WebSocket 只推送 `Op:UpdateNode(id=1, x=10)` 而非全量 JSON，前端只重渲染受影响子图。

### 4. 语义快照隔离增强 (Enhanced Semantic Isolation)

**优化目标**: 处理高并发下的多模态冲突。

- **预测性冲突检测**: 基于历史操作序列训练简单的统计模型。如果用户习惯在 "添加节点" 后立即 "修改文本"，AI 在生成节点后应锁定文本属性短暂时间。
- **多模态冲突**: 不仅检测 ID/位置冲突，还检测语义冲突（如用户删除了 "Login" 节点，AI 却在给 "Login" 添加连线）。
- **分级修复策略**:
  1.  `Auto-fix`: 简单的位置重叠 → 自动弹开 (Force-layout nudge)。
  2.  `Re-reason`: 引用节点消失 → AI 重新生成逻辑。
  3.  `Rollback`: 破坏性冲突 → 回滚到快照点并通知用户。

### 5. 布局与几何计算 (Layout & Geometry)

**优化目标**: 解决 "牵一发而动全身" 的布局跳变问题。

- **认知地图保持 (Mental Map Preservation)**: 在布局算法中加入 "节点移动距离惩罚项"。新布局应尽可能保留旧布局的相对位置，只调整新节点和拥挤区域。
- **动态空间分区 (Dynamic Spatial Partitioning)**:
  - **热力图分析**: 实时统计用户近 1 分钟的鼠标轨迹和点击操作。
  - **动态避让**: AI 自动寻找 "冷区" (Cold Zone) 进行生成，而非固定的九宫格。

### 6. 投机执行 (Speculative Execution)

**优化目标**: 零延迟体验。

- **历史行为预测**: 建立 `UserActionGraph`。如用户常在画 "Condition Node" 后画两条分支，AI 可在用户画菱形时，后台预生成两个分支占位符。
- **快速回滚 (Fast Rollback)**: 投机操作标记为 `pending` 状态（前端虚线显示）。用户进行不符操作时，原子化撤销所有 `pending` 变更，无副作用。

### 7. 数据与性能 (Data & Performance)

**优化目标**: 支持大规模协作。

- **Event Sourcing**: 存储操作日志序列 (`LogStore`) 而非仅最终状态。支持时间旅行调试和细粒度冲突解决。
- **异步任务队列**: 引入 `Celery` 或 `TaskQueue` 处理耗时任务（如全图自动布局、图像生成），避免阻塞 WebSocket 主循环。

---

## 五、执行流程示例 (Enhanced)

**用户输入**: "把支付模块移到右边，并加个退款流程"

### Phase 1: Cognition & Routing

- **GraphCognition**: 检测到 "支付模块" 包含 5 个节点。
- **Partitioning**: 计算出右侧区域有空闲 (Cold Zone)。
- **Router**: 识别为 `CompositeTask` (Move + Gen)。
  - SubTask A: Move (Tier 1 Model)
  - SubTask B: Gen (Tier 2 Model)

### Phase 2: Parallel Reasoning

- **Mutator Agent (Move)**: 生成移动 Op，计算向量 (dx, dy)。
- **Generator Agent (Gen)**: 这里并行预生成 "退款申请" -> "审核" -> "退款成功" 的逻辑序列。

### Phase 3: Layout Solving

- **LayoutEngine**:
  - 应用移动向量。
  - 对新生成的退款流程应用 **增量力导向算法**，锚点固定在 "支付模块" 下游。
  - 检查是否覆盖用户当前视野中心 (User Vision Focus)。

### Phase 4: Transaction & Commit

- **SemanticMonitor**: 检查移动期间用户是否删除了 "支付模块" 中的节点。
  - 无冲突 -> **Commit**。
  - WebSocket 推送增量 Ops。

---

## 六、性能基准 (KPIs)

| 指标                  | 目标       | 优化手段              |
| --------------------- | ---------- | --------------------- |
| **E2E 延迟**          | < 2s       | 动态路由 + 投机执行   |
| **首字节时间 (TTFB)** | < 300ms    | 增量认知 + 流式输出   |
| **布局稳定性**        | < 10% 偏移 | 认知地图保持算法      |
| **冲突自动解决率**    | > 90%      | 预测性检测 + 自动修复 |
| **Token 效率**        | +70%       | 差分摘要 + 增量更新   |
