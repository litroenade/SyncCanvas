import { beforeEach, describe, expect, it } from 'vitest';

import {
  AI_CONVERSATION_MODE_COPY,
  DEFAULT_DIAGRAM_ENTRY_FAMILIES,
  DIAGRAM_AGENT_COPY,
  DIAGRAM_ENTRY_COPY,
  DIAGRAM_FAMILY_REGISTRY,
  MANAGED_DIAGRAM_COPY,
  MERMAID_PREVIEW_CONFIG,
  MERMAID_PREVIEW_COPY,
  PREVIEW_CANVAS_COPY,
  VIRTUAL_CANVAS_COPY,
  formatManagedDiagramWarningSummary,
  getDiagramFamilyLabel,
  getDiagramQuickPrompts,
  localizeManagedDiagramReason,
} from './diagramRegistry';
import { useLocaleStore } from '../stores/useLocaleStore';

describe('diagramRegistry', () => {
  beforeEach(() => {
    useLocaleStore.getState().setLocale('en-US');
  });

  it('returns quick prompts for the default entry families in order', () => {
    expect(getDiagramQuickPrompts()).toEqual([
      'Create a layered platform architecture diagram with orchestration, retrieval, serving, and observability.',
      'Create a transformer stack diagram with embeddings, encoder/decoder blocks, and attention flow.',
      'Sketch a ReAct loop with reasoning, tool action, observation, memory, and answer stages.',
      'Create a retrieval-augmented generation pipeline diagram with ingestion, indexing, retrieval, and generation.',
    ]);
    expect(DEFAULT_DIAGRAM_ENTRY_FAMILIES).toEqual([
      'layered_architecture',
      'transformer_stack',
      'react_loop',
      'rag_pipeline',
    ]);
  });

  it('returns the configured prompts for a selected family subset', () => {
    expect(getDiagramQuickPrompts(['technical_blueprint', 'static_structure'])).toEqual([
      'Create a technical blueprint diagram showing racks, runtime nodes, storage arrays, and infrastructure links.',
      'Create a static structure diagram with classes, interfaces, repositories, and dependencies.',
    ]);
  });

  it('keeps metadata populated for every known family', () => {
    Object.values(DIAGRAM_FAMILY_REGISTRY).forEach((entry) => {
      expect(entry.label.length).toBeGreaterThan(0);
      expect(entry.description.length).toBeGreaterThan(0);
      expect(entry.starterPrompt.length).toBeGreaterThan(0);
    });
  });

  it('centralizes entry copy and Mermaid preview defaults', () => {
    expect(DIAGRAM_ENTRY_COPY.emptyStateTitle).toBe('AI Canvas Agent');
    expect(DIAGRAM_ENTRY_COPY.inputPlaceholder).toContain('create or edit');
    expect(DIAGRAM_AGENT_COPY.rebuild.normalActionLabel).toBe('Rebuild diagram');
    expect(MANAGED_DIAGRAM_COPY.createNew.headline).toBe('Create diagram');
    expect(MERMAID_PREVIEW_CONFIG.parser.themeVariables.fontSize).toBe('16px');
    expect(MERMAID_PREVIEW_CONFIG.convert.regenerateIds).toBe(true);
    expect(MERMAID_PREVIEW_COPY.previewLabel).toBe('Preview');
    expect(PREVIEW_CANVAS_COPY.addToCanvasLabel).toBe('Add to canvas');
    expect(PREVIEW_CANVAS_COPY.addedLabel).toBe('Added');
    expect(VIRTUAL_CANVAS_COPY.addedLabel).toBe('Added');
    expect(AI_CONVERSATION_MODE_COPY.mermaid.label).toBe('Mermaid');
  });

  it('returns stable display labels for known and unknown families', () => {
    expect(getDiagramFamilyLabel('paper_figure')).toBe('Paper Figure');
    expect(getDiagramFamilyLabel('clip')).toBe('CLIP');
    expect(getDiagramFamilyLabel('llm_stack')).toBe('LLM Stack');
    expect(getDiagramFamilyLabel('layered_architecture')).toBe('Layered Architecture');
    expect(getDiagramFamilyLabel('technical_blueprint')).toBe('Technical Blueprint');
    expect(getDiagramFamilyLabel('custom_family')).toBe('custom_family');
    expect(getDiagramFamilyLabel(undefined)).toBe('Unknown family');
  });

  it('normalizes managed-diagram copy helpers', () => {
    expect(localizeManagedDiagramReason('You can only edit one managed diagram at a time.')).toBe(
      MANAGED_DIAGRAM_COPY.defaultConflictReason,
    );
    expect(localizeManagedDiagramReason('Custom reason')).toBe('Custom reason');
    expect(formatManagedDiagramWarningSummary(3)).toBe('3 warnings');
  });

  it('switches registry copy when locale changes', () => {
    useLocaleStore.getState().setLocale('zh-CN');

    expect(DIAGRAM_ENTRY_COPY.emptyStateTitle).toBe('\u0041\u0049 \u753b\u5e03\u52a9\u624b');
    expect(MANAGED_DIAGRAM_COPY.createNew.headline).toBe('\u521b\u5efa\u56fe\u8868');
    expect(formatManagedDiagramWarningSummary(3)).toBe('3 \u6761\u544a\u8b66');
  });
});
