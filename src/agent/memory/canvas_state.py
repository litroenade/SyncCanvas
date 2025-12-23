"""
画布状态感知
"""

from typing import Dict, Any, List, Optional
from collections import Counter

from src.logger import get_logger

logger = get_logger(__name__)


class CanvasStateProvider:
    """画布状态感知服务

    为 Agent 提供画布当前状态的上下文信息。

    功能:
    - 元素类型统计
    - 文本内容提取
    - 版本历史摘要
    - 多模态快照 (预留)
    """

    def get_element_summary(self, elements: List[Dict[str, Any]]) -> str:
        """生成画布元素摘要

        Args:
            elements: Excalidraw 元素列表

        Returns:
            自然语言描述，如 "画布包含: 5个矩形, 3个箭头, 2个文本框"
        """
        if not elements:
            return "画布为空"

        # 统计元素类型
        type_counts: Counter = Counter()
        texts: List[str] = []

        for el in elements:
            if el.get("isDeleted"):
                continue

            el_type = el.get("type", "unknown")
            type_counts[el_type] += 1

            # 收集文本内容
            if el_type == "text" and el.get("text"):
                text = el["text"][:50]  # 截断
                texts.append(text)

        if not type_counts:
            return "画布为空"

        # 类型映射
        type_names = {
            "rectangle": "矩形",
            "ellipse": "椭圆",
            "diamond": "菱形",
            "arrow": "箭头",
            "line": "线条",
            "text": "文本",
            "freedraw": "手绘",
            "image": "图片",
        }

        parts = []
        for el_type, count in type_counts.most_common():
            name = type_names.get(el_type, el_type)
            parts.append(f"{count}个{name}")

        summary = f"画布包含: {', '.join(parts)}"

        # 添加部分文本内容
        if texts:
            sample_texts = texts[:3]
            summary += f"\n文本内容: {', '.join(sample_texts)}"
            if len(texts) > 3:
                summary += f" 等{len(texts)}项"

        return summary

    def get_version_info(self, room_id: str) -> Dict[str, Any]:
        """获取版本控制信息

        Args:
            room_id: 房间 ID

        Returns:
            版本信息字典
        """
        # 版本信息需要数据库会话，暂时返回无历史
        # TODO: 后续通过 AgentContext 传入版本信息
        return {"has_history": False, "message": "版本信息暂未启用"}

    def get_version_summary(self, room_id: str) -> str:
        """生成版本历史摘要文本"""
        info = self.get_version_info(room_id)

        if not info.get("has_history"):
            return "无历史版本"

        latest = info.get("latest_commit", {})
        return f"最近提交: {latest.get('message', '未知')} (by {latest.get('author', '匿名')})"

    async def get_multimodal_snapshot(self, room_id: str) -> Optional[bytes]:
        """获取画布多模态快照 (预留接口)

        TODO: 实现画布截图功能，用于多模态 LLM

        Args:
            room_id: 房间 ID

        Returns:
            PNG 图片字节，或 None
        """
        # 预留接口，后续实现
        logger.debug("多模态快照接口被调用 (room=%s), 暂未实现", room_id)
        return None

    def build_context_prompt(
        self,
        elements: List[Dict[str, Any]],
        room_id: str,
    ) -> str:
        """构建完整的画布上下文 Prompt

        Args:
            elements: 画布元素列表
            room_id: 房间 ID

        Returns:
            注入到系统 Prompt 的上下文文本
        """
        parts = []

        # 元素摘要
        element_summary = self.get_element_summary(elements)
        parts.append(f"【当前画布状态】\n{element_summary}")

        # 版本信息
        version_summary = self.get_version_summary(room_id)
        parts.append(f"【版本历史】\n{version_summary}")

        return "\n\n".join(parts)


# 全局实例
canvas_state_provider: CanvasStateProvider = CanvasStateProvider()
