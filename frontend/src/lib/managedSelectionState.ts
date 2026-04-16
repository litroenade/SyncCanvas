import type { ManagedDiagramTarget } from '../types';

function sameWarnings(
  left: readonly string[],
  right: readonly string[],
): boolean {
  if (left.length !== right.length) {
    return false;
  }

  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) {
      return false;
    }
  }

  return true;
}

export function isSameManagedSelection(
  left: ManagedDiagramTarget | null,
  right: ManagedDiagramTarget | null,
): boolean {
  if (left === right) {
    return true;
  }

  if (!left || !right) {
    return false;
  }

  return left.mode === right.mode
    && left.canEdit === right.canEdit
    && left.reason === right.reason
    && left.diagramId === right.diagramId
    && left.semanticId === right.semanticId
    && left.semanticPath === right.semanticPath
    && left.editScope === right.editScope
    && left.title === right.title
    && left.family === right.family
    && left.managedState === right.managedState
    && left.warningCount === right.warningCount
    && left.selectedCount === right.selectedCount
    && sameWarnings(left.warnings, right.warnings);
}

export function coalesceManagedSelection(
  previous: ManagedDiagramTarget | null,
  next: ManagedDiagramTarget | null,
): ManagedDiagramTarget | null {
  return isSameManagedSelection(previous, next) ? previous : next;
}
