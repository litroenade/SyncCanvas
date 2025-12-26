"""文本计算模块

提供文本尺寸估算和居中计算
"""

from typing import Tuple
from dataclasses import dataclass


@dataclass
class FontMetrics:
    """字体度量参数"""

    font_size: float = 18
    font_family: int = 1  # 1=Hand-drawn, 2=Normal, 3=Code
    line_height: float = 1.25

    @property
    def char_width_ratio(self) -> float:
        """字符宽度与字号的比率

        不同字符类型的估算：
        - ASCII: 约 0.6
        - 中文: 约 1.0
        """
        return 0.6  # 默认使用混合估算

    @property
    def cjk_char_width_ratio(self) -> float:
        """CJK (中日韩) 字符宽度比率"""
        return 1.0


def is_cjk_char(char: str) -> bool:
    """判断是否为 CJK（中日韩）字符

    覆盖的 Unicode 范围:
    - CJK 统一汉字: 4E00-9FFF
    - CJK 扩展 A: 3400-4DBF
    - CJK 扩展 B-F: 20000-2FA1F
    - 韩文音节: AC00-D7AF
    - 平假名: 3040-309F
    - 片假名: 30A0-30FF
    - CJK 符号和标点: 3000-303F
    - 全角 ASCII: FF00-FFEF
    """
    code = ord(char)
    return (
        (0x4E00 <= code <= 0x9FFF)  # CJK 统一汉字
        or (0x3400 <= code <= 0x4DBF)  # CJK 扩展 A
        or (0x20000 <= code <= 0x2FA1F)  # CJK 扩展 B-F
        or (0xAC00 <= code <= 0xD7AF)  # 韩文音节
        or (0x3040 <= code <= 0x309F)  # 平假名
        or (0x30A0 <= code <= 0x30FF)  # 片假名
        or (0x3000 <= code <= 0x303F)  # CJK 符号和标点
        or (0xFF00 <= code <= 0xFFEF)  # 全角字符
    )


def estimate_text_width(
    text: str, font_size: float = 18, font_family: int = 1
) -> float:
    """估算文本渲染宽度

    使用字符类型分类计算：
    - ASCII 字符: 0.6 * font_size
    - CJK 字符: 1.0 * font_size

    Args:
        text: 文本内容
        font_size: 字号
        font_family: 字体系列 (未使用，保留兼容)

    Returns:
        估算的像素宽度
    """
    width = 0.0
    for char in text:
        if is_cjk_char(char):
            width += font_size * 1.0
        else:
            width += font_size * 0.6
    return width


def estimate_text_height(
    text: str, font_size: float = 18, line_height: float = 1.25
) -> float:
    """估算文本渲染高度

    Args:
        text: 文本内容
        font_size: 字号
        line_height: 行高倍数

    Returns:
        估算的像素高度
    """
    lines = text.count("\n") + 1
    return font_size * line_height * lines


def estimate_text_size(
    text: str, font_size: float = 18, font_family: int = 1, line_height: float = 1.25
) -> Tuple[float, float]:
    """估算文本渲染尺寸

    Returns:
        (width, height) 元组
    """
    width = estimate_text_width(text, font_size, font_family)
    height = estimate_text_height(text, font_size, line_height)
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
