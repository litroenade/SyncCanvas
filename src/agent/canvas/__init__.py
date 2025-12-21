"""包名称: canvas
功能说明: 画布后端和布局引擎
"""

from src.agent.canvas.backend import get_canvas_backend, CanvasBackend
from src.agent.canvas.layout import (
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
    "LayoutConfig",
    "LayoutDirection",
    "LayoutResult",
    "calculate_layout",
    "get_theme_colors",
    "THEME_COLORS",
]
