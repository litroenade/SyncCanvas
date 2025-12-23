"""
画布模块 (兼容层)

所有功能已迁移到 agent.core 和 agent.lib.canvas
"""

from src.agent.core.backend import (
    get_canvas_backend,
    CanvasBackend,
    init_canvas_backend,
)
from src.agent.lib.canvas.layout import (
    LayoutConfig,
    LayoutDirection,
    LayoutResult,
    calculate_layout,
    get_theme_colors,
    THEME_COLORS,
)

__all__ = [
    "get_canvas_backend",
    "CanvasBackend",
    "init_canvas_backend",
    "LayoutConfig",
    "LayoutDirection",
    "LayoutResult",
    "calculate_layout",
    "get_theme_colors",
    "THEME_COLORS",
]
