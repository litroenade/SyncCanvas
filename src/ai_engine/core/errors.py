"""模块名称: errors
主要功能: AI Engine 错误定义和处理

统一的错误类型定义，用于更好的错误处理和用户反馈。
"""

from enum import Enum
from typing import Optional, Any, Dict


class ErrorCode(Enum):
    """错误代码枚举"""
    
    # 通用错误 (1xxx)
    UNKNOWN = 1000
    VALIDATION_ERROR = 1001
    TIMEOUT = 1002
    CANCELLED = 1003
    
    # LLM 错误 (2xxx)
    LLM_CONNECTION = 2001
    LLM_TIMEOUT = 2002
    LLM_RATE_LIMIT = 2003
    LLM_INVALID_RESPONSE = 2004
    LLM_CONTENT_FILTER = 2005
    
    # 工具错误 (3xxx)
    TOOL_NOT_FOUND = 3001
    TOOL_INVALID_ARGS = 3002
    TOOL_EXECUTION_ERROR = 3003
    TOOL_TIMEOUT = 3004
    
    # 房间错误 (4xxx)
    ROOM_NOT_FOUND = 4001
    ROOM_BUSY = 4002
    ROOM_LOCK_TIMEOUT = 4003
    
    # Agent 错误 (5xxx)
    AGENT_MAX_ITERATIONS = 5001
    AGENT_INVALID_STATE = 5002


class AIEngineError(Exception):
    """AI Engine 基础异常类
    
    所有 AI Engine 相关异常的基类。
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        return f"[{self.code.name}] {self.message}"


class LLMError(AIEngineError):
    """LLM 相关异常"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.LLM_CONNECTION,
        **kwargs
    ):
        super().__init__(message, code, **kwargs)


class ToolError(AIEngineError):
    """工具执行异常"""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        code: ErrorCode = ErrorCode.TOOL_EXECUTION_ERROR,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["tool_name"] = tool_name
        super().__init__(message, code, details=details, **kwargs)
        self.tool_name = tool_name


class RoomError(AIEngineError):
    """房间相关异常"""
    
    def __init__(
        self,
        message: str,
        room_id: str,
        code: ErrorCode = ErrorCode.ROOM_NOT_FOUND,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["room_id"] = room_id
        super().__init__(message, code, details=details, **kwargs)
        self.room_id = room_id


class AgentError(AIEngineError):
    """Agent 执行异常"""
    
    def __init__(
        self,
        message: str,
        agent_name: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["agent_name"] = agent_name
        super().__init__(message, code, details=details, **kwargs)
        self.agent_name = agent_name


class ValidationError(AIEngineError):
    """参数验证异常"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details=details, **kwargs)


# ==================== 错误处理工具函数 ====================

def safe_json_parse(text: str, default: Any = None) -> Any:
    """安全解析 JSON
    
    Args:
        text: JSON 字符串
        default: 解析失败时的默认值
        
    Returns:
        解析结果或默认值
    """
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate_error_message(message: str, max_length: int = 200) -> str:
    """截断过长的错误信息
    
    Args:
        message: 原始错误信息
        max_length: 最大长度
        
    Returns:
        截断后的信息
    """
    if len(message) <= max_length:
        return message
    return message[:max_length - 3] + "..."


def format_exception(exc: Exception, include_traceback: bool = False) -> str:
    """格式化异常信息
    
    Args:
        exc: 异常对象
        include_traceback: 是否包含堆栈
        
    Returns:
        格式化后的错误信息
    """
    import traceback
    
    if isinstance(exc, AIEngineError):
        msg = str(exc)
    else:
        msg = f"{type(exc).__name__}: {str(exc)}"
    
    if include_traceback:
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        msg += "\n" + "".join(tb[-3:])  # 只保留最后 3 行
    
    return truncate_error_message(msg, 500)

