"""模块名称: deps
主要功能: 依赖注入 (Re-export from auth.utils)
"""

from src.auth.utils import get_current_user, get_current_user_optional

__all__ = ["get_current_user", "get_current_user_optional"]
