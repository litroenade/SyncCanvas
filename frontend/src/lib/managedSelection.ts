import type { DiagramBundle, ManagedDiagramTarget } from '../types';

export function isKnownSemantic(bundle: DiagramBundle, semanticId: string): boolean {
  if (semanticId === 'diagram.title') {
    return true;
  }

  return bundle.spec.components.some((component) => component.id === semanticId)
    || bundle.spec.annotations.some((annotation) => annotation.id === semanticId)
    || bundle.spec.connectors.some((connector) => connector.id === semanticId);
}

export function resolveSharedSemanticId(
  bundle: DiagramBundle,
  semanticIds: string[],
): string | undefined {
  if (semanticIds.length === 0) {
    return undefined;
  }

  if (semanticIds.length === 1) {
    const candidate = semanticIds[0];
    return isKnownSemantic(bundle, candidate) ? candidate : undefined;
  }

  const splitIds = semanticIds.map((semanticId) => semanticId.split('.'));
  let prefix = [...splitIds[0]];

  for (let index = 1; index < splitIds.length; index += 1) {
    while (
      prefix.length > 0
      && prefix.some((part, partIndex) => splitIds[index][partIndex] !== part)
    ) {
      prefix = prefix.slice(0, -1);
    }
  }

  while (prefix.length > 0) {
    const candidate = prefix.join('.');
    if (isKnownSemantic(bundle, candidate)) {
      return candidate;
    }
    prefix = prefix.slice(0, -1);
  }

  return undefined;
}

export function normalizeManagedScope(
  bundle: DiagramBundle,
  semanticIds: string[],
): string[] {
  const normalized: string[] = [];

  semanticIds.forEach((semanticId) => {
    if (!isKnownSemantic(bundle, semanticId)) {
      return;
    }
    if (!normalized.includes(semanticId)) {
      normalized.push(semanticId);
    }
  });

  if (normalized.length > 0) {
    return normalized;
  }

  return bundle.spec.components.map((component) => component.id);
}

export function refreshManagedSelectionTarget(
  bundle: DiagramBundle,
  selection: ManagedDiagramTarget,
): ManagedDiagramTarget | null {
  if (selection.mode === 'create_new' || selection.mode === 'conflict') {
    return selection;
  }

  if (!selection.diagramId || selection.diagramId !== bundle.spec.diagramId) {
    return null;
  }

  const semanticId = selection.semanticId && isKnownSemantic(bundle, selection.semanticId)
    ? selection.semanticId
    : undefined;
  const mode = selection.mode === 'semantic' && semanticId ? 'semantic' : 'diagram';

  return {
    ...selection,
    mode,
    semanticId,
    semanticPath: semanticId,
    editScope: mode,
    title: bundle.summary.title,
    family: bundle.summary.family,
    managedState: bundle.state.managedState,
    warnings: [...bundle.state.warnings],
    warningCount: bundle.state.warnings.length,
  };
}
