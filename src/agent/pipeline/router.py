"""模块名称: router
主要功能: 动态 LLM 路由器

Phase 2 核心组件 - 实现真正的动态模型选择:
- 任务分类: 根据输入和画布复杂度判断任务 Tier
- 性能追踪: 维护每个模型的实时性能指标
- 动态选择: 基于 Tier + 指标 + 约束选择最优模型

设计理念:
- Tier 1 (Real-time): 简单任务用小模型
- Tier 2 (Reasoning): 复杂任务用大模型
- 实时反馈: 根据历史性能动态调整
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from src.config import config, ModelConfig
from src.agent.pipeline.cognition import CanvasState
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 常量 ====================

METRICS_WINDOW_SIZE = 100
DEFAULT_MAX_LATENCY_MS = 5000


# ==================== 任务分级 ====================


class TaskTier(Enum):
    """任务分级

    影响模型选择策略。
    """

    TIER_1_REALTIME = "tier1"  # 快速响应: 简单修改、位置调整
    TIER_2_REASONING = "tier2"  # 深度推理: 复杂生成、架构设计


class TaskIntent(Enum):
    """任务意图类型"""

    GENERATE = "generate"  # 生成新图表
    MODIFY = "modify"  # 修改现有元素
    QUERY = "query"  # 查询/问答
    DELETE = "delete"  # 删除操作
    LAYOUT = "layout"  # 布局调整
    UNKNOWN = "unknown"


@dataclass
class Task:
    """任务描述"""

    tier: TaskTier
    intent: TaskIntent
    complexity: float = 0.5  # 0.0-1.0
    keywords: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


# ==================== 任务分类器 ====================


class TaskClassifier:
    """任务分类器

    分析用户输入和画布状态，判断任务类型和复杂度。
    """

    # Tier 2 关键词 (复杂任务)
    COMPLEX_KEYWORDS = [
        "流程图",
        "架构图",
        "数据流图",
        "时序图",
        "类图",
        "ER图",
        "系统设计",
        "完整",
        "详细",
        "复杂",
        "flowchart",
        "architecture",
        "diagram",
        "system",
        "complete",
        "detailed",
    ]

    # Tier 1 关键词 (简单任务)
    SIMPLE_KEYWORDS = [
        "移动",
        "删除",
        "修改",
        "调整",
        "重命名",
        "添加一个",
        "move",
        "delete",
        "rename",
        "adjust",
        "add one",
    ]

    # 意图关键词映射
    INTENT_KEYWORDS = {
        TaskIntent.GENERATE: [
            "画",
            "创建",
            "生成",
            "设计",
            "做",
            "draw",
            "create",
            "generate",
            "design",
        ],
        TaskIntent.MODIFY: [
            "修改",
            "更新",
            "改",
            "调整",
            "modify",
            "update",
            "change",
            "adjust",
        ],
        TaskIntent.DELETE: ["删除", "移除", "清除", "delete", "remove", "clear"],
        TaskIntent.LAYOUT: [
            "布局",
            "排列",
            "整理",
            "对齐",
            "layout",
            "arrange",
            "align",
        ],
        TaskIntent.QUERY: [
            "什么",
            "如何",
            "为什么",
            "解释",
            "what",
            "how",
            "why",
            "explain",
        ],
    }

    def classify(
        self, user_input: str, canvas_state: Optional[CanvasState] = None
    ) -> Task:
        """分类任务

        Args:
            user_input: 用户输入
            canvas_state: 画布状态 (可选)

        Returns:
            Task: 任务描述
        """
        input_lower = user_input.lower()
        keywords_found = []

        # 检测意图
        intent = self._detect_intent(input_lower)

        # 检测复杂度
        complexity = self._estimate_complexity(input_lower, canvas_state)

        # 确定 Tier
        tier = (
            TaskTier.TIER_2_REASONING if complexity > 0.5 else TaskTier.TIER_1_REALTIME
        )

        # 收集匹配的关键词
        for kw in self.COMPLEX_KEYWORDS + self.SIMPLE_KEYWORDS:
            if kw.lower() in input_lower:
                keywords_found.append(kw)

        return Task(
            tier=tier,
            intent=intent,
            complexity=complexity,
            keywords=keywords_found,
        )

    def _detect_intent(self, text: str) -> TaskIntent:
        """检测任务意图"""
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return intent
        return TaskIntent.UNKNOWN

    def _estimate_complexity(
        self, text: str, canvas_state: Optional[CanvasState]
    ) -> float:
        """估算任务复杂度 (0.0 - 1.0)"""
        score = 0.5  # 基础分

        # 关键词影响
        for kw in self.COMPLEX_KEYWORDS:
            if kw.lower() in text:
                score += 0.15

        for kw in self.SIMPLE_KEYWORDS:
            if kw.lower() in text:
                score -= 0.15

        # 文本长度影响
        if len(text) > 100:
            score += 0.1
        elif len(text) < 20:
            score -= 0.1

        # 画布状态影响
        if canvas_state:
            if canvas_state.element_count > 10:
                score += 0.1  # 复杂画布
            elif canvas_state.is_empty:
                score += 0.05  # 从零开始需要更多规划

        # 数字检测 (可能涉及多步骤)
        numbers = re.findall(r"\d+", text)
        if numbers and any(int(n) > 3 for n in numbers):
            score += 0.1

        return max(0.0, min(1.0, score))


# ==================== 性能指标 ====================


@dataclass
class PerformanceMetrics:
    """模型性能指标"""

    model_name: str = ""
    latencies: Deque[float] = field(
        default_factory=lambda: deque(maxlen=METRICS_WINDOW_SIZE)
    )
    total_calls: int = 0
    success_calls: int = 0
    last_call_time: float = 0.0

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return 1.0 - (self.success_calls / self.total_calls)

    @property
    def latency_p50(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        return sorted_lat[len(sorted_lat) // 2]

    @property
    def latency_p99(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    def record(self, latency_ms: float, success: bool) -> None:
        self.latencies.append(latency_ms)
        self.total_calls += 1
        if success:
            self.success_calls += 1
        self.last_call_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "total_calls": self.total_calls,
            "error_rate": round(self.error_rate, 4),
            "latency_p50": round(self.latency_p50, 2),
            "latency_p99": round(self.latency_p99, 2),
        }


# ==================== LLM 路由器 ====================


@dataclass
class ModelScore:
    """模型评分结果"""

    model_name: str
    config: ModelConfig
    score: float = 0.0
    reason: str = ""


class LLMRouter:
    """动态 LLM 路由器

    实现真正的模型选择逻辑:
    1. 根据 TaskTier 筛选候选模型
    2. 根据性能指标评分
    3. 返回最优模型配置
    """

    # Tier 模型映射 (基于模型名称启发式)
    TIER_1_PATTERNS = ["8b", "7b", "14b", "qwen", "llama", "gemma", "mini", "flash"]
    TIER_2_PATTERNS = [
        "gpt-4",
        "claude-3",
        "deepseek-v3",
        "70b",
        "72b",
        "opus",
        "sonnet",
    ]

    _instance: Optional["LLMRouter"] = None

    def __new__(cls) -> "LLMRouter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._classifier = TaskClassifier()
        self._initialized = True
        logger.info("[LLMRouter] 初始化完成")

    @property
    def classifier(self) -> TaskClassifier:
        """获取任务分类器"""
        return self._classifier

    def _get_or_create_metrics(self, model_name: str) -> PerformanceMetrics:
        if model_name not in self._metrics:
            self._metrics[model_name] = PerformanceMetrics(model_name=model_name)
        return self._metrics[model_name]

    def record_call(
        self, model_name: str, latency_ms: float, success: bool = True
    ) -> None:
        """记录模型调用"""
        metrics = self._get_or_create_metrics(model_name)
        metrics.record(latency_ms, success)
        logger.debug(
            "[LLMRouter] 记录: model=%s, latency=%.1fms, success=%s",
            model_name,
            latency_ms,
            success,
        )

    def get_metrics(self, model_name: str) -> PerformanceMetrics:
        return self._get_or_create_metrics(model_name)

    def get_all_metrics(self) -> Dict[str, Dict]:
        return {name: m.to_dict() for name, m in self._metrics.items()}

    def _get_available_models(self) -> List[ModelConfig]:
        """获取所有可用模型"""
        models = []

        # 从 model_groups 获取
        if hasattr(config.config.ai, "model_groups"):
            for _, group in config.config.ai.model_groups.items():
                models.append(group)

        # 如果没有配置，使用默认
        if not models:
            default = ModelConfig(
                provider=config.llm_provider,
                model=config.llm_model,
                base_url=config.llm_base_url,
                api_key=config.llm_api_key,
            )
            models.append(default)

            if config.llm_fallback_api_key:
                fallback = ModelConfig(
                    provider=config.llm_fallback_provider,
                    model=config.llm_fallback_model,
                    base_url=config.llm_fallback_base_url,
                    api_key=config.llm_fallback_api_key,
                )
                models.append(fallback)

        return models

    def _is_tier_match(self, model_name: str, tier: TaskTier) -> bool:
        """检查模型是否匹配 Tier"""
        model_lower = model_name.lower()

        if tier == TaskTier.TIER_1_REALTIME:
            return any(p in model_lower for p in self.TIER_1_PATTERNS)
        else:
            return any(p in model_lower for p in self.TIER_2_PATTERNS)

    def _score_model(
        self,
        model: ModelConfig,
        tier: TaskTier,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ModelScore:
        """评分模型"""
        constraints = constraints or {}
        metrics = self._get_or_create_metrics(model.model)

        score = 100.0
        reasons = []

        # 错误率惩罚
        if metrics.error_rate > 0:
            penalty = 50 * metrics.error_rate
            score -= penalty
            reasons.append(f"错误率 -{penalty:.1f}")

        # 延迟惩罚
        if metrics.latency_p50 > 0:
            latency_penalty = 10 * (metrics.latency_p50 / 1000)
            score -= latency_penalty
            reasons.append(f"延迟 -{latency_penalty:.1f}")

        # 延迟约束检查
        max_latency = constraints.get("max_latency_ms", DEFAULT_MAX_LATENCY_MS)
        if metrics.latency_p50 > max_latency:
            score -= 100
            reasons.append(f"超出延迟限制 {max_latency}ms")

        # Tier 匹配奖励
        if self._is_tier_match(model.model, tier):
            score += 30
            reasons.append(f"Tier {tier.value} 匹配 +30")

        return ModelScore(
            model_name=model.model,
            config=model,
            score=score,
            reason="; ".join(reasons) if reasons else "基础分",
        )

    def select(
        self,
        tier: TaskTier = TaskTier.TIER_2_REASONING,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ModelConfig:
        """选择最优模型

        这是核心路由方法,基于 Tier 和约束选择模型。

        Args:
            tier: 任务分级
            constraints: 约束条件 (如 max_latency_ms)

        Returns:
            ModelConfig: 选中的模型配置
        """
        models = self._get_available_models()

        if not models:
            raise ValueError("没有可用的模型配置")

        # 评分所有模型
        scored = [self._score_model(m, tier, constraints) for m in models]
        scored.sort(key=lambda x: x.score, reverse=True)

        selected = scored[0]

        logger.info(
            "[LLMRouter] 选择模型: %s (tier=%s, score=%.1f, reason=%s)",
            selected.model_name,
            tier.value,
            selected.score,
            selected.reason,
        )

        return selected.config

    def classify_and_select(
        self,
        user_input: str,
        canvas_state: Optional[CanvasState] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> tuple[Task, ModelConfig]:
        """分类任务并选择模型

        便捷方法,合并分类和选择。

        Returns:
            (Task, ModelConfig): 任务描述和模型配置
        """
        task = self._classifier.classify(user_input, canvas_state)
        model = self.select(task.tier, constraints)
        return task, model

    def reset_metrics(self, model_name: Optional[str] = None) -> None:
        if model_name:
            if model_name in self._metrics:
                self._metrics[model_name] = PerformanceMetrics(model_name=model_name)
        else:
            self._metrics.clear()
        logger.info("[LLMRouter] 已重置指标: %s", model_name or "全部")


# ==================== 工厂函数 ====================


def get_router() -> LLMRouter:
    """获取 LLMRouter 单例"""
    return LLMRouter()


def get_classifier() -> TaskClassifier:
    """获取 TaskClassifier"""
    return TaskClassifier()
