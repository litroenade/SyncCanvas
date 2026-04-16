"""文本计算工具

用于估算文本尺寸和居中位置
"""

from typing import Tuple


def estimate_text_size(
    text: str,
    font_size: float = 18,
    font_family: int = 1,
    line_height: float = 1.25,
) -> Tuple[float, float]:
    """估算文本尺寸

    根据文本内容和字体参数估算宽度和高度。
    这是一个简化的估算，实际渲染可能有差异。

    Args:
        text: 文本内容
        font_size: 字体大小
        font_family: 字体系列 (1=Virgil, 2=Helvetica, 3=Cascadia)
        line_height: 行高倍数

    Returns:
        (width, height) 元组
    """
    if not text:
        return (0, font_size * line_height)

    lines = text.split("\n")

    # 字符宽度系数（根据字体调整）
    # Virgil 手写字体较宽，Helvetica 较窄
    char_width_factor = {
        1: 0.6,  # Virgil
        2: 0.5,  # Helvetica
        3: 0.55,  # Cascadia
    }.get(font_family, 0.6)

    # 中文字符通常是英文的 2 倍宽
    chinese_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    ascii_count = len(text.replace("\n", "")) - chinese_count

    # 估算宽度
    width = (ascii_count * char_width_factor + chinese_count * 1.0) * font_size

    # 估算高度
    height = len(lines) * font_size * line_height

    return (width, height)


def calculate_centered_position(
    container_x: float,
    container_y: float,
    container_width: float,
    container_height: float,
    text: str,
    font_size: float = 18,
    font_family: int = 1,
    line_height: float = 1.25,
) -> Tuple[float, float, float, float]:
    """计算文本在容器内居中的位置

    Args:
        container_*: 容器的位置和尺寸
        text: 文本内容
        font_*: 字体参数

    Returns:
        (text_x, text_y, text_width, text_height) 元组
    """
    text_width, text_height = estimate_text_size(
        text, font_size, font_family, line_height
    )

    # 居中计算
    text_x = container_x + (container_width - text_width) / 2
    text_y = container_y + (container_height - text_height) / 2

    return (text_x, text_y, text_width, text_height)
