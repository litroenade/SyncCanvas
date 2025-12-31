"""Mermaid 生成工具

提供 Mermaid 流程图代码生成功能
"""

import re
from src.agent.core.llm import LLMClient
from src.logger import get_logger

logger = get_logger(__name__)


async def generate_mermaid_code(prompt: str) -> dict:
    """使用 AI 生成 Mermaid 流程图代码

    根据用户的自然语言描述，生成对应的 Mermaid 流程图语法代码。

    Args:
        prompt: 流程图描述

    Returns:
        dict: 包含 code 和 status
    """
    system_prompt = """你是一个 Mermaid 流程图专家。根据用户的描述生成对应的 Mermaid 流程图代码。

规则：
1. 只返回 Mermaid 代码，不要任何解释、markdown 代码块或其他文本
2. 使用 flowchart TD (从上到下) 或 flowchart LR (从左到右) 语法
3. 节点 ID 使用简短的英文字母，如 A, B, C 或 start, end
4. 中文标签放在方括号 [] 或花括号 {} 内
5. 开始节点使用 ([...])，结束节点使用 ([...])，判断条件使用 {...}
6. 条件分支用 |条件| 标注
7. 保持图表简洁清晰

示例输出格式：
flowchart TD
    A([开始]) --> B{判断条件}
    B -->|是| C[执行操作A]
    B -->|否| D[执行操作B]
    C --> E([结束])
    D --> E"""

    user_prompt = f"请为以下内容生成 Mermaid 流程图代码：\n\n{prompt}"

    try:
        llm = LLMClient()
        response = await llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        # 提取 Mermaid 代码 - response 是 LLMResponse 对象
        code = (response.content or "").strip()

        # 如果返回了 markdown 代码块，提取其中的内容
        match = re.search(r"```(?:mermaid)?\n?([\s\S]*?)```", code)
        if match:
            code = match.group(1).strip()

        # 确保代码以 flowchart 开头
        if not code.startswith(("flowchart", "graph")):
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith(("flowchart", "graph")):
                    code = "\n".join(lines[i:])
                    break

        logger.info("Mermaid 生成成功", extra={"code_length": len(code)})
        return {"code": code, "status": "success"}

    except Exception as e:
        logger.error("Mermaid 生成失败: %s", e, exc_info=True)
        return {
            "code": f"flowchart TD\n    A([错误]) --> B[{str(e)[:50]}]",
            "status": "error",
        }
