# AI Agent 架构文档

> 更新时间: 2025-12-11

## 一、系统概述

SyncCanvas 采用 **State-Aware Neuro-Symbolic Pipeline**（状态感知的神经符号流水线）架构，实现 AI 辅助的协作白板编辑。

**核心设计理念：**
1. **拓扑与几何解耦** - LLM 负责逻辑正确性，布局算法负责视觉正确性
2. **状态注入** - 实时图摘要作为上下文，解决多用户协作下的指代模糊
3. **黑板模式** - Yjs/CRDT 作为共享状态，Agent 和用户都是"专家"

---

## 二、现有架构 (Current)

### 数据流

```
User Input → PlannerAgent → ReAct Loop → Tool Call (create_element) → Yjs → Broadcast
                                              ↑
                                        含 x,y 坐标
```

### 组件

| 组件 | 文件 | 职责 |
|------|------|------|
| PlannerAgent | `src/agent/agents/planner.py` | 主协调者，处理用户请求 |
| CanvaserAgent | `src/agent/agents/canvaser.py` | 专业绘图，复杂流程图 |
| BaseAgent | `src/agent/core/agent.py` | ReAct 循环、重试、超时控制 |
| LLMClient | `src/agent/core/llm.py` | LLM 调用，支持主/备用故障转移 |
| Tools | `src/agent/tools/` | 画布操作工具（含坐标参数） |

### 问题

1. LLM 直接输出坐标 → 不可靠
2. 没有状态注入 → 无法理解画布当前状态
3. 单一模型 → 无法针对任务优化

---

## 三、目标架构 (Target)

### 数据流

```
User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: State Hydration (状态注入)                          │
│   - summarize_graph(ydoc) → 轻量拓扑描述                      │
│   - 构建增强 Prompt: {用户指令, 图摘要, 历史}                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Intent Routing (意图路由)                           │
│   - Router 分类: create / modify / qa                        │
│   - 分发给对应 Agent                                         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Logical Reasoning (逻辑推理)                        │
│   - Generator: 生成逻辑 JSON (无坐标)                         │
│   - Mutator: 输出操作序列 [delete, add, connect]             │
│   - Grounding: 指代消解 "那个红框" → node-123                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Geometric Solving (几何求解)                        │
│   - LayoutEngine 计算坐标                                     │
│   - 子图增量布局 (保持心智地图稳定)                            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Sync & Broadcast (同步广播)                         │
│   - CRDT Transaction                                         │
│   - WebSocket 推送                                           │
└─────────────────────────────────────────────────────────────┘
```

### Agent 角色定义

| Agent | 推荐模型 | 职责 |
|-------|----------|------|
| Router | 小模型 (gpt-4o-mini) | 意图分类，任务分发 |
| Generator | 推理强 (DeepSeek-V3) | 从零生成图结构 |
| Mutator | 快速响应 (Qwen-14B) | 增量修改现有结构 |
| Grounding | 小模型 | 指代消解，空间定位 |

### 任务模型配置

```toml
[model_task_config.router]
model_list = ["gpt-4o-mini"]
temperature = 0.1

[model_task_config.generator]
model_list = ["deepseek-v3", "qwen-14b"]
temperature = 0.3

[model_task_config.mutator]
model_list = ["qwen-14b"]
temperature = 0.2

[model_task_config.grounding]
model_list = ["gpt-4o-mini"]
temperature = 0.1
```

---

## 四、核心创新点

### 1. 拓扑与几何解耦

```python
# 现在：LLM 输出坐标
create_flowchart_node(x=100, y=200, text="A")

# 目标：LLM 只输出逻辑
add_node(label="A", type="process", parent="root")
# 坐标由 LayoutEngine 计算
```

### 2. 状态注入 (State Hydration)

```python
def summarize_graph(ydoc) -> str:
    """将画布转为轻量拓扑描述"""
    # 输出: "Nodes: [A(start), B(process)], Edges: [A→B]"
    # 不含坐标，减少 Token 消耗
```

### 3. 指代消解 (Grounding)

用户说："在左边那个红框下面加一个圆"

```python
def ground_reference(query: str, graph_summary: str) -> str:
    """将模糊指代转为具体 ID"""
    # "左边红框" → "node-abc-123"
```

### 4. 子图增量布局

```python
def apply_layout(ops: List[Op], graph: Graph) -> Graph:
    affected = identify_affected_subgraph(ops)  # 只识别受影响节点
    return layout_subgraph(graph, affected)      # 避免全图重排
```

---

## 五、数据流转示例

**用户输入：** "在 Login 和 Home 之间加一个 2FA 验证"

**Phase 1 输出：**
```json
{
  "instruction": "Insert '2FA' between 'Login' and 'Home'",
  "graph_summary": "Nodes: [Login(n1), Home(n2)], Edges: [n1→n2]"
}
```

**Phase 3 输出：**
```json
{
  "actions": [
    {"op": "delete_edge", "src": "n1", "tgt": "n2"},
    {"op": "add_node", "id": "n3", "label": "2FA"},
    {"op": "add_edge", "src": "n1", "tgt": "n3"},
    {"op": "add_edge", "src": "n3", "tgt": "n2"}
  ]
}
```

**Phase 4 输出：**
```json
{
  "updates": [
    {"id": "n3", "x": 100, "y": 150},
    {"id": "n2", "x": 100, "y": 300}
  ]
}
```

---

## 六、相关文件

| 文件 | 用途 |
|------|------|
| `src/agent/core/agent.py` | BaseAgent 基类 |
| `src/agent/core/llm.py` | LLM 客户端 |
| `src/agent/agents/planner.py` | PlannerAgent |
| `src/agent/agents/canvaser.py` | CanvaserAgent |
| `src/agent/tools/` | 画布操作工具 |
| `src/agent/prompts/` | Prompt 模板 |
