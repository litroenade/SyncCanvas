from typing import Final, Tuple


ROUNDNESS_TYPE_ADAPTIVE: Final[int] = 2
"""自适应圆角（用于线条/箭头）"""

ROUNDNESS_TYPE_PROPORTIONAL: Final[int] = 3
"""比例圆角（用于矩形/椭圆）"""

FONT_FAMILY_VIRGIL: Final[int] = 1
"""Virgil 手写风格"""

FONT_FAMILY_HELVETICA: Final[int] = 2
"""Helvetica 正常字体"""

FONT_FAMILY_CASCADIA: Final[int] = 3
"""Cascadia 代码字体"""

SEED_RANGE: Final[Tuple[int, int]] = (1, 100000)
"""元素种子值范围"""

VERSION_NONCE_RANGE: Final[Tuple[int, int]] = (1, 1000000000)
"""版本随机数范围"""

# 这些是 Excalidraw 的默认值，通常不需要修改

DEFAULT_OPACITY: Final[int] = 100
"""默认不透明度 (0-100)"""

DEFAULT_ROUGHNESS: Final[int] = 1
"""默认粗糙度 (Excalidraw 手绘风格)"""

DEFAULT_STROKE_WIDTH: Final[int] = 2
"""默认描边宽度"""

DEFAULT_LINE_HEIGHT: Final[float] = 1.25
"""默认行高"""

DEFAULT_ARROW_FOCUS: Final[float] = 0.0
"""箭头绑定的焦点值"""

DEFAULT_ARROW_GAP: Final[float] = 8.0
"""箭头与元素边缘的默认间距"""
