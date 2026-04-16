const MERMAID_BLOCK_REGEX = /```mermaid\s*([\s\S]*?)```/i;
const MERMAID_DIRECT_DEFINITION_REGEX =
  /^(?:%%\{[\s\S]*?\}%%\s*)?(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|journey|gantt|pie|mindmap|gitGraph|timeline)\b/i;

export function extractMermaidCode(content: string): string | null {
  const trimmed = content.trim();

  if (!trimmed) {
    return null;
  }

  const match = trimmed.match(MERMAID_BLOCK_REGEX);
  if (match?.[1]?.trim()) {
    return match[1].trim();
  }

  if (MERMAID_DIRECT_DEFINITION_REGEX.test(trimmed)) {
    return trimmed;
  }

  return null;
}
