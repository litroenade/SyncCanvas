/**
 * ToolProgress - AI 工具执行进度组件
 * 
 * 显示 AI Agent 工具调用的实时进度。
 */

import { useMemo } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import './ToolProgress.css';

// ==================== 类型定义 ====================

export interface ToolStep {
    /** 步骤编号 */
    stepNumber: number;
    /** 思考过程 */
    thought?: string;
    /** 工具名称 */
    action?: string;
    /** 工具参数 */
    actionInput?: Record<string, unknown>;
    /** 执行结果摘要 */
    observation?: string;
    /** 是否成功 */
    success?: boolean;
    /** 执行耗时 (ms) */
    latencyMs?: number;
    /** 状态: pending/running/done/error */
    status: 'pending' | 'running' | 'done' | 'error';
}

interface ToolProgressProps {
    /** 工具执行步骤列表 */
    steps: ToolStep[];
    /** 是否正在执行 */
    isRunning?: boolean;
    /** 是否折叠显示 */
    collapsed?: boolean;
    /** 自定义样式 */
    className?: string;
}

// ==================== 工具图标映射 ====================

const TOOL_ICONS: Record<string, string> = {
    create_flowchart_node: '📦',
    connect_nodes: '🔗',
    get_canvas_bounds: '📐',
    create_element: '✏️',
    list_elements: '📋',
    delete_elements: '🗑️',
    clear_canvas: '🧹',
    fetch_webpage: '🌐',
    calculate: '🧮',
    get_current_time: '🕐',
};

// ==================== 主组件 ====================

export function ToolProgress({
    steps,
    isRunning = false,
    collapsed = false,
    className = '',
}: ToolProgressProps) {
    const summary = useMemo(() => {
        const total = steps.length;
        const done = steps.filter(s => s.status === 'done').length;
        const errors = steps.filter(s => s.status === 'error').length;
        return { total, done, errors };
    }, [steps]);

    if (steps.length === 0) {
        return null;
    }

    return (
        <div className={`tool-progress ${className} ${collapsed ? 'collapsed' : ''}`}>
            {/* 进度摘要 */}
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
                        ? `执行中... (${summary.done}/${summary.total})`
                        : summary.errors > 0
                            ? `完成 ${summary.done}/${summary.total}，${summary.errors} 个错误`
                            : `已完成 ${summary.total} 步`
                    }
                </span>
            </div>

            {/* 步骤列表 */}
            {!collapsed && (
                <div className="step-list">
                    {steps.map((step) => (
                        <ToolStepItem key={step.stepNumber} step={step} />
                    ))}
                </div>
            )}
        </div>
    );
}

// ==================== 单个步骤组件 ====================

interface ToolStepItemProps {
    step: ToolStep;
}

function ToolStepItem({ step }: ToolStepItemProps) {
    const icon = step.action ? TOOL_ICONS[step.action] || '⚙️' : '💭';

    return (
        <div className={`step-item ${step.status}`}>
            <div className="step-header">
                <span className="step-number">#{step.stepNumber}</span>
                <span className="step-icon">{icon}</span>
                <span className="step-action">{step.action || '思考中'}</span>
                <span className="step-status">
                    {step.status === 'running' && <Loader2 size={12} className="spin" />}
                    {step.status === 'done' && <CheckCircle size={12} className="success" />}
                    {step.status === 'error' && <XCircle size={12} className="error" />}
                </span>
                {step.latencyMs !== undefined && step.status === 'done' && (
                    <span className="step-latency">{step.latencyMs}ms</span>
                )}
            </div>

            {step.thought && (
                <div className="step-thought">{step.thought}</div>
            )}

            {step.observation && step.status !== 'pending' && (
                <div className={`step-observation ${step.success ? 'success' : 'error'}`}>
                    {step.observation.length > 100
                        ? step.observation.slice(0, 100) + '...'
                        : step.observation
                    }
                </div>
            )}
        </div>
    );
}

export default ToolProgress;
