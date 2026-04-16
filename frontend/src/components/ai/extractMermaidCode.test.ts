import { describe, expect, it } from 'vitest';

import { extractMermaidCode } from './extractMermaidCode';

describe('extractMermaidCode', () => {
  it('extracts Mermaid code from fenced blocks', () => {
    expect(
      extractMermaidCode('Before\n```mermaid\nflowchart TD\n  A-->B\n```\nAfter'),
    ).toBe('flowchart TD\n  A-->B');
  });

  it('accepts raw Mermaid definitions for direct rendering', () => {
    expect(
      extractMermaidCode('flowchart LR\n  Start([Start]) --> Step[Process] --> End([End])'),
    ).toBe('flowchart LR\n  Start([Start]) --> Step[Process] --> End([End])');
  });

  it('accepts Mermaid init directives before the definition', () => {
    expect(
      extractMermaidCode('%%{init: {"theme":"neutral"}}%%\nstateDiagram-v2\n  [*] --> Ready'),
    ).toBe('%%{init: {"theme":"neutral"}}%%\nstateDiagram-v2\n  [*] --> Ready');
  });

  it('returns null for plain text prompts', () => {
    expect(extractMermaidCode('draw an A* search workflow with heuristics')).toBeNull();
  });
});
