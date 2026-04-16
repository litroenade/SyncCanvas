/**
 * ToolProgress - AI 工具执行进度组件
 *
 * 显示 AI Agent 工具调用的实时进度。
 */

import { useMemo } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

import { useI18n } from '../../i18n';
import './ToolProgress.css';

export interface ToolStep {
  stepNumber: number;
  thought?: string;
  action?: string;
  actionInput?: Record<string, unknown>;
  observation?: string;
  success?: boolean;
  latencyMs?: number;
  status: 'pending' | 'running' | 'done' | 'error';
}

interface ToolProgressProps {
  steps: ToolStep[];
  isRunning?: boolean;
  collapsed?: boolean;
  className?: string;
}

const TOOL_ICONS: Record<string, string> = {
  create_flowchart_node: '📝',
  connect_nodes: '🔗',
  get_canvas_bounds: '📐',
  create_element: '✏️',
  list_elements: '📋',
  delete_elements: '🗑️',
  clear_canvas: '🧹',
  fetch_webpage: '🌐',
  calculate: '🧮',
  get_current_time: '🕒',
};

export function ToolProgress({
  steps,
  isRunning = false,
  collapsed = false,
  className = '',
}: ToolProgressProps) {
  const { t } = useI18n();

  const summary = useMemo(() => {
    const total = steps.length;
    const done = steps.filter((step) => step.status === 'done').length;
    const errors = steps.filter((step) => step.status === 'error').length;
    return { total, done, errors };
  }, [steps]);

  if (steps.length === 0) {
    return null;
  }

  return (
    <div className={`tool-progress ${className} ${collapsed ? 'collapsed' : ''}`}>
      <div className="progress-summary">
        <span className="summary-icon">
          {isRunning ? (
            <Loader2 size={16} className="spin" />
          ) : summary.errors > 0 ? (
            <XCircle size={16} className="error" />
          ) : (
            <CheckCircle size={16} className="success" />
          )}
        </span>
        <span className="summary-text">
          {isRunning
            ? t('toolProgress.running', { done: summary.done, total: summary.total })
            : summary.errors > 0
              ? t('toolProgress.finishedWithErrors', {
                  done: summary.done,
                  total: summary.total,
                  errors: summary.errors,
                })
              : t('toolProgress.finished', { total: summary.total })}
        </span>
      </div>

      {!collapsed && (
        <div className="step-list">
          {steps.map((step) => (
            <ToolStepItem key={step.stepNumber} step={step} thinkingLabel={t('toolProgress.thinking')} />
          ))}
        </div>
      )}
    </div>
  );
}

interface ToolStepItemProps {
  step: ToolStep;
  thinkingLabel: string;
}

function ToolStepItem({ step, thinkingLabel }: ToolStepItemProps) {
  const icon = step.action ? TOOL_ICONS[step.action] || '⚙️' : '💭';

  return (
    <div className={`step-item ${step.status}`}>
      <div className="step-header">
        <span className="step-number">#{step.stepNumber}</span>
        <span className="step-icon">{icon}</span>
        <span className="step-action">{step.action || thinkingLabel}</span>
        <span className="step-status">
          {step.status === 'running' && <Loader2 size={12} className="spin" />}
          {step.status === 'done' && <CheckCircle size={12} className="success" />}
          {step.status === 'error' && <XCircle size={12} className="error" />}
        </span>
        {step.latencyMs !== undefined && step.status === 'done' && (
          <span className="step-latency">{step.latencyMs}ms</span>
        )}
      </div>

      {step.thought && <div className="step-thought">{step.thought}</div>}

      {step.observation && step.status !== 'pending' && (
        <div className={`step-observation ${step.success ? 'success' : 'error'}`}>
          {step.observation.length > 100
            ? `${step.observation.slice(0, 100)}...`
            : step.observation}
        </div>
      )}
    </div>
  );
}

export default ToolProgress;
