import type { ManagedDiagramTarget } from '../types';
import {
  MANAGED_DIAGRAM_COPY,
  formatManagedDiagramWarningSummary,
  getDiagramFamilyLabel,
  localizeManagedDiagramReason,
} from './diagramRegistry';

export type ManagedDiagramSeverity = 'normal' | 'warning' | 'blocked';

export interface ManagedDiagramStatusView {
  mode: ManagedDiagramTarget['mode'];
  severity: ManagedDiagramSeverity;
  canEdit: boolean;
  headline: string;
  description: string;
  reason?: string;
  warnings: string[];
  warningCount: number;
  warningSummary?: string;
  stateLabel?: string;
  metaItems: string[];
  showRebuild: boolean;
}

const MANAGED_STATE_LABELS: Record<
  NonNullable<ManagedDiagramTarget['managedState']>,
  string
> = MANAGED_DIAGRAM_COPY.stateLabels;

export function getManagedDiagramStateLabel(
  managedState: ManagedDiagramTarget['managedState'] | undefined,
): string | undefined {
  if (!managedState) {
    return undefined;
  }

  return MANAGED_STATE_LABELS[managedState];
}

function buildMetaItems(target: ManagedDiagramTarget | null): string[] {
  if (!target || target.mode === 'create_new' || target.mode === 'conflict') {
    return [];
  }

  const items: string[] = [];
  const seen = new Set<string>();
  const pushItem = (item: string | undefined) => {
    if (!item || seen.has(item)) return;
    seen.add(item);
    items.push(item);
  };

  pushItem(target.title);
  pushItem(getDiagramFamilyLabel(target.family));
  pushItem(target.semanticPath);

  const stateLabel = getManagedDiagramStateLabel(target.managedState);
  if (stateLabel) {
    pushItem(`\u72b6\u6001: ${stateLabel}`);
  }

  return items;
}

function shouldShowRebuild(target: ManagedDiagramTarget): boolean {
  return (
    Boolean(target.diagramId)
    && target.canEdit
    && (target.managedState === 'semi_managed' || target.managedState === 'unmanaged')
  );
}

export function getManagedDiagramStatusView(
  target: ManagedDiagramTarget | null | undefined,
): ManagedDiagramStatusView {
  if (!target || target.mode === 'create_new') {
    return {
      mode: 'create_new',
      severity: 'normal',
      canEdit: true,
      headline: MANAGED_DIAGRAM_COPY.createNew.headline,
      description: MANAGED_DIAGRAM_COPY.createNew.description,
      warnings: [],
      warningCount: 0,
      metaItems: [],
      showRebuild: false,
    };
  }

  const reason = localizeManagedDiagramReason(
    target.reason,
    target.mode === 'conflict' || target.canEdit === false
      ? MANAGED_DIAGRAM_COPY.defaultConflictReason
      : undefined,
  );

  if (target.mode === 'conflict' || target.canEdit === false) {
    return {
      mode: target.mode,
      severity: 'blocked',
      canEdit: false,
      headline: MANAGED_DIAGRAM_COPY.blocked.headline,
      description: MANAGED_DIAGRAM_COPY.blocked.description,
      reason,
      warnings: [],
      warningCount: 0,
      metaItems: buildMetaItems(target),
      showRebuild: false,
    };
  }

  const isWarningState = target.managedState === 'semi_managed' || target.managedState === 'unmanaged';
  const warnings = isWarningState ? [...target.warnings] : [];
  const warningCount = isWarningState ? warnings.length : 0;
  const severity: ManagedDiagramSeverity = isWarningState ? 'warning' : 'normal';
  const description = target.mode === 'semantic'
    ? MANAGED_DIAGRAM_COPY.editable.semanticDescription
    : MANAGED_DIAGRAM_COPY.editable.diagramDescription;

  return {
    mode: target.mode,
    severity,
    canEdit: true,
    headline: target.mode === 'semantic'
      ? MANAGED_DIAGRAM_COPY.editable.semanticHeadline
      : MANAGED_DIAGRAM_COPY.editable.diagramHeadline,
    description,
    reason,
    warnings,
    warningCount,
    warningSummary: warningCount > 0 ? formatManagedDiagramWarningSummary(warningCount) : undefined,
    stateLabel: getManagedDiagramStateLabel(target.managedState),
    metaItems: buildMetaItems(target),
    showRebuild: shouldShowRebuild(target),
  };
}
