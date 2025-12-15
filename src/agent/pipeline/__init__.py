"""包名称: pipeline
功能说明: 5-Phase Agent 执行管道

编排 Agent 执行流程:
1. State Hydration - 画布状态认知
2. Intent Routing - 意图路由
3. Reasoning - 推理
4. Layout - 布局计算
5. Transaction - 事务提交
"""

from src.agent.pipeline.executor import (
    AgentPipeline,
    PipelineResult,
    PipelineMetrics,
    create_pipeline,
)
from src.agent.pipeline.cognition import (
    GraphCognition,
    CanvasState,
    CanvasBounds,
    ElementInfo,
    get_cognition,
)
from src.agent.pipeline.router import (
    LLMRouter,
    TaskClassifier,
    TaskTier,
    Task,
    PerformanceMetrics,
    get_router,
)
from src.agent.pipeline.reasoning import (
    CanvasReasoner,
    LogicalReasoner,
    LogicalOp,
    OpType,
    ReasoningResult,
    ReasoningMode,
)
from src.agent.pipeline.layout import (
    LayoutEngine,
    LayoutConfig,
    PositionedOp,
    get_layout_engine,
)
from src.agent.pipeline.transaction import (
    SemanticTransaction,
    TransactionResult,
    Conflict,
    get_transaction,
)

__all__ = [
    # executor
    "AgentPipeline",
    "PipelineResult",
    "PipelineMetrics",
    "create_pipeline",
    # cognition
    "GraphCognition",
    "CanvasState",
    "CanvasBounds",
    "ElementInfo",
    "get_cognition",
    # router
    "LLMRouter",
    "TaskClassifier",
    "TaskTier",
    "Task",
    "PerformanceMetrics",
    "get_router",
    # reasoning
    "CanvasReasoner",
    "LogicalReasoner",
    "LogicalOp",
    "OpType",
    "ReasoningResult",
    "ReasoningMode",
    # layout
    "LayoutEngine",
    "LayoutConfig",
    "PositionedOp",
    "get_layout_engine",
    # transaction
    "SemanticTransaction",
    "TransactionResult",
    "Conflict",
    "get_transaction",
]
