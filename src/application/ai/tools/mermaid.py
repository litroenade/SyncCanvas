"""Mermaid generation helpers."""

import re

from src.infra.ai.llm import LLMClient
from src.infra.logging import get_logger

logger = get_logger(__name__)

MERMAID_BLOCK_RE = re.compile(r"```(?:mermaid)?\s*([\s\S]*?)```", re.IGNORECASE)
MERMAID_DEFINITION_RE = re.compile(
    r"(?is)(?:%%\{[\s\S]*?\}%%\s*)?"
    r"(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|"
    r"erDiagram|journey|gantt|pie|mindmap|gitGraph|timeline)\b[\s\S]*"
)


def normalize_mermaid_code(content: str) -> str:
    """Extract Mermaid code from mixed model output and keep the diagram definition."""

    candidate = content.strip()
    if not candidate:
        return ""

    fenced = MERMAID_BLOCK_RE.search(candidate)
    if fenced and fenced.group(1).strip():
        candidate = fenced.group(1).strip()

    definition = MERMAID_DEFINITION_RE.search(candidate)
    if definition:
        return definition.group(0).strip()

    return candidate


async def generate_mermaid_code(prompt: str) -> dict:
    """Generate Mermaid code from natural language input."""

    system_prompt = """You are a Mermaid diagram expert.

Return Mermaid code only. Do not add explanations, bullet lists, or prose.

Choose the Mermaid diagram type that best matches the request:
- flowchart / graph for algorithms, branching logic, search loops, pipelines, and control flow
- stateDiagram-v2 for state transitions, automata, and lifecycle changes
- sequenceDiagram for protocol steps or message exchange
- classDiagram for data structures and object relationships
- mindmap for concept decomposition

For algorithm-heavy prompts such as A*, Dijkstra, beam search, dynamic programming,
MCTS, schedulers, or custom research algorithms, make the key decision points explicit:
frontier/open set, closed set, heuristic evaluation, loop conditions, updates, and exit states.

Use concise stable ids and readable labels. Keep the diagram compact and structurally correct.
"""

    user_prompt = f"Generate Mermaid code for the following request:\n\n{prompt}"

    try:
        llm = LLMClient()
        response = await llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        code = normalize_mermaid_code(response.content or "")
        if not code:
            raise ValueError("Empty Mermaid response")

        logger.info("Mermaid generation succeeded", extra={"code_length": len(code)})
        return {"code": code, "status": "success"}

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Mermaid generation failed: %s", exc, exc_info=True)
        return {
            "code": f"flowchart TD\n    A([Error]) --> B[{str(exc)[:50]}]",
            "status": "error",
        }
