"""模块名称: general_tools
主要功能: 通用 AI 工具，包括文本分析、知识整理等

提供非绘图场景下的通用工具支持。
"""

from typing import Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

from src.ai_engine.core.tools import registry, ToolCategory
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 参数 Schema ====================

class AnalyzeTextArgs(BaseModel):
    """分析文本的参数"""
    text: str = Field(..., description="要分析的文本内容")
    analysis_type: str = Field(
        "summary",
        description="分析类型: summary(摘要), keywords(关键词), structure(结构分析)"
    )


class CreateOutlineArgs(BaseModel):
    """创建大纲的参数"""
    topic: str = Field(..., description="主题")
    depth: int = Field(2, description="大纲层级深度 (1-3)")
    items_per_level: int = Field(3, description="每级的项目数 (2-5)")


class GetCurrentTimeArgs(BaseModel):
    """获取当前时间的参数"""
    format: str = Field("%Y-%m-%d %H:%M:%S", description="时间格式")


class CalculateArgs(BaseModel):
    """计算的参数"""
    expression: str = Field(..., description="数学表达式，如 '2+3*4', 'sqrt(16)'")


# ==================== 工具实现 ====================

@registry.register(
    "get_current_time",
    "获取当前时间",
    GetCurrentTimeArgs,
    category=ToolCategory.GENERAL,
)
async def get_current_time(
    format: str = "%Y-%m-%d %H:%M:%S",
) -> Dict[str, Any]:
    """获取当前时间
    
    Args:
        format: 时间格式字符串
        
    Returns:
        dict: 包含当前时间的结果
    """
    now = datetime.now()
    
    try:
        formatted = now.strftime(format)
    except ValueError:
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "status": "success",
        "time": formatted,
        "timestamp": int(now.timestamp()),
        "iso": now.isoformat(),
    }


@registry.register(
    "calculate",
    "执行安全的数学计算",
    CalculateArgs
)
async def calculate(
    expression: str,
) -> Dict[str, Any]:
    """执行数学计算
    
    支持基本运算和常用数学函数。
    
    Args:
        expression: 数学表达式
        
    Returns:
        dict: 计算结果
    """
    import math
    
    # 允许的函数和常量
    safe_dict = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
    }
    
    # 清理表达式
    expr = expression.strip()
    
    # 安全检查
    forbidden = ["import", "exec", "eval", "__", "open", "file", "os", "sys"]
    for word in forbidden:
        if word in expr.lower():
            return {
                "status": "error",
                "message": f"表达式包含不允许的关键词: {word}"
            }
    
    try:
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        
        logger.info(f"计算: {expr} = {result}")
        
        return {
            "status": "success",
            "expression": expr,
            "result": result,
            "message": f"{expr} = {result}"
        }
    except Exception as e:
        return {
            "status": "error",
            "expression": expr,
            "message": f"计算错误: {str(e)}"
        }


@registry.register(
    "create_outline",
    "为主题创建结构化大纲，可用于后续绘制思维导图或流程图",
    CreateOutlineArgs
)
async def create_outline(
    topic: str,
    depth: int = 2,
    items_per_level: int = 3,
) -> Dict[str, Any]:
    """创建主题大纲 (占位实现)
    
    注意: 这是一个结构化的占位实现，实际内容需要 LLM 生成。
    
    Args:
        topic: 主题
        depth: 层级深度
        items_per_level: 每级项目数
        
    Returns:
        dict: 大纲结构
    """
    depth = max(1, min(3, depth))
    items_per_level = max(2, min(5, items_per_level))
    
    return {
        "status": "info",
        "topic": topic,
        "depth": depth,
        "items_per_level": items_per_level,
        "message": "大纲创建需要 LLM 生成具体内容。请根据主题自行组织内容结构。",
        "template": {
            "title": topic,
            "children": [
                {"title": f"子主题 {i+1}", "children": []} 
                for i in range(items_per_level)
            ]
        }
    }


@registry.register(
    "thinking",
    "思考和推理工具，用于复杂问题的分步分析",
    AnalyzeTextArgs
)
async def thinking(
    text: str,
    analysis_type: str = "summary",
) -> Dict[str, Any]:
    """思考/分析工具 (占位)
    
    这是一个占位工具，用于标记 Agent 的思考过程。
    实际的分析由 LLM 在对话中完成。
    
    Args:
        text: 要分析的内容
        analysis_type: 分析类型
        
    Returns:
        dict: 分析结果占位
    """
    return {
        "status": "info",
        "input": text[:200] + "..." if len(text) > 200 else text,
        "analysis_type": analysis_type,
        "message": "思考过程已记录。请继续分析并给出结论。"
    }
