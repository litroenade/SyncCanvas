from typing import Final, Tuple

DEFAULT_NODE_WIDTH: Final[float] = 160.0
"""流程图节点默认宽度"""

DEFAULT_NODE_HEIGHT: Final[float] = 70.0
"""流程图节点默认高度"""

DEFAULT_DIAMOND_MIN_SIZE: Final[float] = 100.0
"""菱形节点最小尺寸"""

DEFAULT_ELLIPSE_MIN_WIDTH: Final[float] = 120.0
"""椭圆节点最小宽度"""

DEFAULT_ELEMENT_SIZE: Final[float] = 100.0
"""通用元素默认尺寸"""

DEFAULT_FONT_SIZE: Final[int] = 18
"""默认字体大小"""

DEFAULT_FONT_SIZE_SMALL: Final[int] = 14
"""小号字体大小（用于标签）"""

DEFAULT_FONT_SIZE_LARGE: Final[int] = 20
"""大号字体大小"""

# Excalidraw 字体系列: 1=Virgil(手写), 2=Helvetica, 3=Cascadia
DEFAULT_FONT_FAMILY: Final[int] = 1
"""默认字体系列 (Virgil 手写风格)"""

DEFAULT_LINE_HEIGHT: Final[float] = 1.25
"""默认行高"""

DEFAULT_STROKE_WIDTH: Final[int] = 2
"""默认描边宽度"""

DEFAULT_OPACITY: Final[int] = 100
"""默认不透明度 (0-100)"""

DEFAULT_ROUGHNESS: Final[int] = 1
"""默认粗糙度 (Excalidraw 手绘风格)"""

# 圆角类型: 2=ADAPTIVE_RADIUS (线条), 3=PROPORTIONAL_RADIUS (形状)
ROUNDNESS_TYPE_ADAPTIVE: Final[int] = 2
"""自适应圆角（用于线条/箭头）"""

ROUNDNESS_TYPE_PROPORTIONAL: Final[int] = 3
"""比例圆角（用于矩形/椭圆）"""

SEED_RANGE: Final[Tuple[int, int]] = (1, 100000)
"""元素种子值范围"""

VERSION_NONCE_RANGE: Final[Tuple[int, int]] = (1, 1000000000)
"""版本随机数范围"""

DEFAULT_ARROW_GAP: Final[float] = 8.0
"""箭头与元素边缘的默认间距"""

DEFAULT_ARROW_FOCUS: Final[float] = 0.0
"""箭头绑定的焦点值"""

DEFAULT_HORIZONTAL_GAP: Final[float] = 60.0
"""元素水平间距"""

DEFAULT_VERTICAL_GAP: Final[float] = 80.0
"""元素垂直间距"""

DEFAULT_START_X: Final[float] = 400.0
"""布局起始 X 坐标"""

DEFAULT_START_Y: Final[float] = 100.0
"""布局起始 Y 坐标"""

# === 路径规划参数 ===
PATHFINDING_GRID_SIZE: Final[float] = 10.0
"""A* 路径规划网格大小（像素）"""

PATHFINDING_OBSTACLE_PADDING: Final[float] = 25.0
"""障碍物边缘间距（像素）"""

PATHFINDING_MAX_ITERATIONS: Final[int] = 2000
"""A* 算法最大迭代次数"""

PATHFINDING_TURN_PENALTY: Final[float] = 0.5
"""路径转弯惩罚系数"""
