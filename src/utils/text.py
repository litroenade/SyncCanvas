"""
文本处理工具
"""

import re
from typing import List, Optional


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """从文本中提取关键词 (简单实现)

    Args:
        text: 原始文本
        max_keywords: 最大关键词数量

    Returns:
        关键词列表
    """
    if not text:
        return []

    # 移除标点和特殊字符
    cleaned = re.sub(r"[^\w\s]", " ", text)

    # 分词并统计词频
    words = cleaned.lower().split()
    word_freq: dict[str, int] = {}

    # 过滤停用词
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "when",
        "up",
        "out",
        "这",
        "是",
        "的",
        "了",
        "在",
        "和",
        "有",
        "就",
        "不",
        "我",
        "你",
    }

    for word in words:
        if len(word) > 2 and word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1

    # 按频率排序
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """清理文本 (移除控制字符、多余空白)

    Args:
        text: 原始文本
        max_length: 可选的最大长度

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 移除控制字符 (保留换行和制表符)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 合并多个空白为单个空格
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # 合并多个换行为最多两个
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 去除首尾空白
    cleaned = cleaned.strip()

    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned
