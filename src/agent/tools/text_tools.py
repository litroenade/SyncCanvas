"""模块名称: text_tools
主要功能: 文本分析和转换工具

提供文本到结构化数据的转换，支持:
- 文本转流程图结构
- Markdown 解析
- 代码结构分析
"""

import re
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from src.agent.registry import registry, ToolCategory
from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 参数 Schema ====================

class ParseFlowTextArgs(BaseModel):
    """解析流程文本的参数"""
    text: str = Field(..., description="描述流程的文本，每行一个步骤，用 -> 表示下一步")
    include_decision: bool = Field(True, description="是否识别判断节点 (包含 '?' 或 '如果' 的行)")


class ParseMarkdownArgs(BaseModel):
    """解析 Markdown 的参数"""
    markdown: str = Field(..., description="Markdown 文本")
    extract_structure: bool = Field(True, description="是否提取标题结构")


class AnalyzeCodeArgs(BaseModel):
    """分析代码结构的参数"""
    code: str = Field(..., description="代码文本")
    language: str = Field("python", description="编程语言")


# ==================== 辅助函数 ====================

def _is_decision_step(text: str) -> bool:
    """判断是否为决策节点"""
    decision_keywords = [
        "?", "？", "如果", "是否", "判断", "检查",
        "if", "whether", "check", "decide", "condition"
    ]
    lower_text = text.lower()
    return any(kw in lower_text for kw in decision_keywords)


def _is_start_end(text: str) -> str:
    """判断是否为开始/结束节点"""
    start_keywords = ["开始", "start", "begin", "初始化"]
    end_keywords = ["结束", "end", "finish", "完成", "done"]

    lower_text = text.lower().strip()

    if any(lower_text.startswith(kw) or lower_text == kw for kw in start_keywords):
        return "start"
    if any(lower_text.startswith(kw) or lower_text == kw for kw in end_keywords):
        return "end"
    return ""


def _clean_step_text(text: str) -> str:
    """清理步骤文本"""
    # 移除序号前缀
    text = re.sub(r"^\d+[\.\)、]\s*", "", text.strip())
    # 移除箭头
    text = re.sub(r"^[-=]>\s*", "", text)
    text = re.sub(r"\s*[-=]>$", "", text)
    return text.strip()


# ==================== 工具实现 ====================

@registry.register(
    "parse_flow_text",
    "将流程描述文本解析为结构化的流程图数据，可用于后续绘图",
    ParseFlowTextArgs,
    category=ToolCategory.GENERAL,
)
async def parse_flow_text(
    text: str,
    include_decision: bool = True,
) -> Dict[str, Any]:
    """解析流程描述文本为结构化数据
    
    输入格式示例:
    ```
    开始
    用户输入账号密码
    验证账号密码是否正确?
    -> 是: 登录成功
    -> 否: 显示错误信息
    结束
    ```
    
    Args:
        text: 流程描述文本
        include_decision: 是否识别判断节点
        
    Returns:
        dict: 包含 nodes 和 edges 的流程图结构
    """
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    if not lines:
        return {
            "status": "error",
            "message": "输入文本为空"
        }

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    current_decision_id: Optional[str] = None

    for i, line in enumerate(lines):
        clean_text = _clean_step_text(line)
        if not clean_text:
            continue

        node_id = f"node_{i}"

        # 检查是否为分支标签 (-> 是: xxx)
        branch_match = re.match(r"^[-=]>\s*(是|否|yes|no|true|false)[:\s]*(.+)$", line, re.IGNORECASE)
        if branch_match and current_decision_id:
            branch_label = branch_match.group(1)
            branch_text = branch_match.group(2).strip()

            # 创建分支节点
            nodes.append({
                "id": node_id,
                "label": branch_text,
                "type": "rectangle",
            })

            # 从判断节点连接到分支
            edges.append({
                "from": current_decision_id,
                "to": node_id,
                "label": branch_label,
            })
            continue

        # 判断节点类型
        start_end = _is_start_end(clean_text)
        if start_end:
            node_type = "ellipse"
        elif include_decision and _is_decision_step(clean_text):
            node_type = "diamond"
            current_decision_id = node_id
        else:
            node_type = "rectangle"
            current_decision_id = None

        nodes.append({
            "id": node_id,
            "label": clean_text,
            "type": node_type,
        })

        # 连接上一个节点 (如果不是分支)
        if len(nodes) > 1 and not branch_match:
            prev_node = nodes[-2]
            # 如果上一个是判断节点，不自动连接
            if prev_node["type"] != "diamond":
                edges.append({
                    "from": prev_node["id"],
                    "to": node_id,
                })

    logger.info("解析流程文本: %d 个节点, %d 条边", len(nodes), len(edges))

    return {
        "status": "success",
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "message": f"成功解析 {len(nodes)} 个步骤"
    }


@registry.register(
    "parse_markdown_structure",
    "解析 Markdown 文本的标题结构，可用于生成思维导图",
    ParseMarkdownArgs,
    category=ToolCategory.GENERAL,
)
async def parse_markdown_structure(
    markdown: str,
    extract_structure: bool = True,
) -> Dict[str, Any]:
    """解析 Markdown 的标题结构
    
    Args:
        markdown: Markdown 文本
        extract_structure: 是否提取层级结构
        
    Returns:
        dict: 包含标题层级结构的数据
    """
    lines = markdown.split("\n")
    headings: List[Dict[str, Any]] = []

    for line in lines:
        # 匹配 Markdown 标题
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({
                "level": level,
                "text": text,
            })

    if not headings:
        return {
            "status": "info",
            "message": "未找到 Markdown 标题",
            "headings": []
        }

    # 构建树形结构
    if extract_structure:
        root = {"text": "Document", "level": 0, "children": []}
        stack = [root]

        for heading in headings:
            node = {"text": heading["text"], "level": heading["level"], "children": []}

            # 找到合适的父节点
            while len(stack) > 1 and stack[-1]["level"] >= heading["level"]:
                stack.pop()

            stack[-1]["children"].append(node)
            stack.append(node)

        return {
            "status": "success",
            "structure": root,
            "heading_count": len(headings),
            "message": f"解析到 {len(headings)} 个标题"
        }

    return {
        "status": "success",
        "headings": headings,
        "heading_count": len(headings),
    }


@registry.register(
    "analyze_code_structure",
    "分析代码结构，提取类、函数等定义，可用于绘制类图",
    AnalyzeCodeArgs,
    category=ToolCategory.GENERAL,
)
async def analyze_code_structure(
    code: str,
    language: str = "python",
) -> Dict[str, Any]:
    """分析代码结构
    
    目前支持 Python 代码的基础结构分析。
    
    Args:
        code: 代码文本
        language: 编程语言
        
    Returns:
        dict: 代码结构信息
    """
    if language.lower() != "python":
        return {
            "status": "info",
            "message": f"暂不支持 {language}，目前仅支持 Python",
            "classes": [],
            "functions": [],
        }

    classes: List[Dict[str, Any]] = []
    functions: List[Dict[str, Any]] = []

    # 简单的正则匹配 (生产环境应使用 AST)
    # 匹配类定义
    class_pattern = r"^class\s+(\w+)(?:\(([^)]*)\))?:"
    for match in re.finditer(class_pattern, code, re.MULTILINE):
        class_name = match.group(1)
        bases = match.group(2) or ""
        classes.append({
            "name": class_name,
            "bases": [b.strip() for b in bases.split(",") if b.strip()],
        })

    # 匹配函数定义
    func_pattern = r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)"
    for match in re.finditer(func_pattern, code, re.MULTILINE):
        func_name = match.group(1)
        params = match.group(2)
        functions.append({
            "name": func_name,
            "params": [p.strip().split(":")[0].strip() for p in params.split(",") if p.strip()],
        })

    return {
        "status": "success",
        "language": language,
        "classes": classes,
        "functions": functions,
        "class_count": len(classes),
        "function_count": len(functions),
        "message": f"找到 {len(classes)} 个类, {len(functions)} 个函数"
    }
