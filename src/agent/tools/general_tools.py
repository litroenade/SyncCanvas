"""模块名称: general_tools
主要功能: 通用 AI 工具
"""
import ast
import math
import operator

from typing import Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

from src.agent.registry import registry, ToolCategory
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 参数 Schema ====================


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
    """获取当前时间"""
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
    """执行数学计算，支持基本运算和常用数学函数"""

    expr = expression.strip()

    # 安全检查
    forbidden = ["import", "exec", "eval", "__", "open", "file", "os", "sys", "lambda"]
    for word in forbidden:
        if word in expr.lower():
            return {"status": "error", "message": f"表达式包含不允许的关键词: {word}"}

    operators_map = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    functions = {
        "abs": abs, "round": round, "min": min, "max": max, "pow": pow,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "exp": math.exp,
    }

    constants = {"pi": math.pi, "e": math.e}

    def safe_eval(node):
        """递归安全求值"""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Num):  # Python 3.7 兼容
            return node.n
        if isinstance(node, ast.Name):
            if node.id in constants:
                return constants[node.id]
            raise ValueError(f"未知变量: {node.id}")
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in operators_map:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            return operators_map[op_type](safe_eval(node.left), safe_eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in operators_map:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            return operators_map[op_type](safe_eval(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("不支持的函数调用方式")
            func_name = node.func.id
            if func_name not in functions:
                raise ValueError(f"不支持的函数: {func_name}")
            return functions[func_name](*[safe_eval(arg) for arg in node.args])
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")

    try:
        tree = ast.parse(expr, mode='eval')
        result = safe_eval(tree.body)
        logger.info("计算: %s = %s", expr, result)
        return {"status": "success", "expression": expr, "result": result}
    except SyntaxError as e:
        return {"status": "error", "expression": expr, "message": f"语法错误: {e}"}
    except ValueError as e:
        return {"status": "error", "expression": expr, "message": f"计算错误: {e}"}
    except ZeroDivisionError:
        return {"status": "error", "expression": expr, "message": "除零错误"}
    except Exception as e:  # pylint: disable=broad-except
        return {"status": "error", "expression": expr, "message": f"计算错误: {e}"}
