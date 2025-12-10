/**
 * ConfigEditor - 通用配置编辑器组件
 * 
 * 支持多种数据类型、元数据驱动渲染和实时保存。
 * 利用 ExtraField 元数据实现密钥隐藏、多行文本、下拉选择等功能。
 */

import { useState, useCallback } from 'react';
import { Eye, EyeOff, Info, Check, X, Loader2 } from 'lucide-react';
import { type ConfigItem } from '../../services/api/config';
import '../../styles/ConfigEditor.css';

// ==================== 类型定义 ====================

interface ConfigEditorProps {
    /** 配置项列表 */
    configs: ConfigItem[];
    /** 保存回调 */
    onSave: (key: string, value: unknown) => Promise<void>;
    /** 是否只读 */
    readOnly?: boolean;
    /** 自定义样式 */
    className?: string;
}

interface FieldState {
    value: string;
    editing: boolean;
    saving: boolean;
    error: string | null;
}

// ==================== 主组件 ====================

export function ConfigEditor({ configs, onSave, readOnly = false, className = '' }: ConfigEditorProps) {
    // 每个字段的编辑状态
    const [fieldStates, setFieldStates] = useState<Record<string, FieldState>>({});

    // 获取字段状态
    const getFieldState = (key: string, originalValue: unknown): FieldState => {
        return fieldStates[key] ?? {
            value: formatValue(originalValue),
            editing: false,
            saving: false,
            error: null,
        };
    };

    // 更新字段状态
    const updateFieldState = (key: string, updates: Partial<FieldState>) => {
        setFieldStates(prev => ({
            ...prev,
            [key]: { ...getFieldState(key, null), ...updates },
        }));
    };

    // 开始编辑
    const startEdit = (key: string, originalValue: unknown) => {
        updateFieldState(key, {
            value: formatValue(originalValue),
            editing: true,
            error: null,
        });
    };

    // 取消编辑
    const cancelEdit = (key: string) => {
        setFieldStates(prev => {
            const newState = { ...prev };
            delete newState[key];
            return newState;
        });
    };

    // 保存字段
    const saveField = useCallback(async (item: ConfigItem) => {
        const state = fieldStates[item.key];
        if (!state) return;

        // 类型转换和验证
        let parsedValue: unknown;
        try {
            parsedValue = parseValue(state.value, item.type);
        } catch (e) {
            updateFieldState(item.key, { error: (e as Error).message });
            return;
        }

        updateFieldState(item.key, { saving: true, error: null });

        try {
            await onSave(item.key, parsedValue);
            // 保存成功，清除编辑状态
            setFieldStates(prev => {
                const newState = { ...prev };
                delete newState[item.key];
                return newState;
            });
        } catch (e) {
            updateFieldState(item.key, {
                saving: false,
                error: (e as Error).message || '保存失败',
            });
        }
    }, [fieldStates, onSave]);

    return (
        <div className={`config-editor ${className}`}>
            {configs.map(item => (
                <ConfigField
                    key={item.key}
                    item={item}
                    state={getFieldState(item.key, item.value)}
                    readOnly={readOnly}
                    onStartEdit={() => startEdit(item.key, item.value)}
                    onCancelEdit={() => cancelEdit(item.key)}
                    onValueChange={(value) => updateFieldState(item.key, { value })}
                    onSave={() => saveField(item)}
                />
            ))}
        </div>
    );
}

// ==================== 单个字段组件 ====================

interface ConfigFieldProps {
    item: ConfigItem;
    state: FieldState;
    readOnly: boolean;
    onStartEdit: () => void;
    onCancelEdit: () => void;
    onValueChange: (value: string) => void;
    onSave: () => void;
}

function ConfigField({
    item,
    state,
    readOnly,
    onStartEdit,
    onCancelEdit,
    onValueChange,
    onSave,
}: ConfigFieldProps) {
    const [showSecret, setShowSecret] = useState(false);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !item.is_textarea) {
            onSave();
        } else if (e.key === 'Escape') {
            onCancelEdit();
        }
    };

    // 渲染输入控件
    const renderInput = () => {
        // 枚举类型 - 下拉选择
        if (item.enum && item.enum.length > 0) {
            return (
                <select
                    value={state.value}
                    onChange={(e) => onValueChange(e.target.value)}
                    onBlur={onSave}
                    disabled={state.saving}
                    className="config-select"
                >
                    {item.enum.map(opt => (
                        <option key={opt} value={opt}>{opt}</option>
                    ))}
                </select>
            );
        }

        // 布尔类型 - 开关
        if (item.type === 'bool') {
            return (
                <label className="config-toggle">
                    <input
                        type="checkbox"
                        checked={state.value === 'true'}
                        onChange={(e) => {
                            onValueChange(e.target.checked ? 'true' : 'false');
                            // 立即保存
                            setTimeout(onSave, 0);
                        }}
                        disabled={state.saving}
                    />
                    <span className="toggle-slider"></span>
                </label>
            );
        }

        // 多行文本
        if (item.is_textarea) {
            return (
                <textarea
                    value={state.value}
                    onChange={(e) => onValueChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={item.placeholder}
                    disabled={state.saving}
                    className="config-textarea"
                    rows={4}
                />
            );
        }

        // 密钥类型
        if (item.is_secret) {
            return (
                <div className="config-secret-input">
                    <input
                        type={showSecret ? 'text' : 'password'}
                        value={state.value}
                        onChange={(e) => onValueChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={item.placeholder || '输入密钥...'}
                        disabled={state.saving}
                        className="config-input"
                    />
                    <button
                        type="button"
                        onClick={() => setShowSecret(!showSecret)}
                        className="secret-toggle"
                    >
                        {showSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                </div>
            );
        }

        // 数字输入
        if (item.type === 'int' || item.type === 'float') {
            return (
                <input
                    type="number"
                    value={state.value}
                    onChange={(e) => onValueChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={onSave}
                    placeholder={item.placeholder}
                    disabled={state.saving}
                    step={item.type === 'float' ? '0.1' : '1'}
                    className="config-input config-number"
                />
            );
        }

        // 默认文本输入
        return (
            <input
                type="text"
                value={state.value}
                onChange={(e) => onValueChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={onSave}
                placeholder={item.placeholder}
                disabled={state.saving}
                className="config-input"
            />
        );
    };

    // 渲染只读值
    const renderReadOnlyValue = () => {
        if (item.is_secret) {
            return <span className="config-value secret">••••••••</span>;
        }
        if (item.type === 'bool') {
            return <span className={`config-value bool ${item.value ? 'true' : 'false'}`}>
                {item.value ? '是' : '否'}
            </span>;
        }
        return <span className="config-value">{formatValue(item.value)}</span>;
    };

    return (
        <div className={`config-field ${state.error ? 'has-error' : ''}`}>
            <div className="config-field-header">
                <label className="config-label">
                    {item.title}
                    {item.required && <span className="required">*</span>}
                </label>
                {item.description && (
                    <span className="config-tooltip" title={item.description}>
                        <Info size={14} />
                    </span>
                )}
            </div>

            <div className="config-field-body">
                {readOnly ? (
                    renderReadOnlyValue()
                ) : state.editing ? (
                    <div className="config-edit-row">
                        {renderInput()}
                        <div className="config-edit-actions">
                            {state.saving ? (
                                <Loader2 size={16} className="spin" />
                            ) : (
                                <>
                                    <button onClick={onSave} className="save-btn" title="保存">
                                        <Check size={16} />
                                    </button>
                                    <button onClick={onCancelEdit} className="cancel-btn" title="取消">
                                        <X size={16} />
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                ) : (
                    <div
                        className="config-display-value"
                        onClick={onStartEdit}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && onStartEdit()}
                    >
                        {renderReadOnlyValue()}
                    </div>
                )}
            </div>

            {state.error && (
                <div className="config-field-error">{state.error}</div>
            )}
        </div>
    );
}

// ==================== 工具函数 ====================

/** 格式化值为字符串 */
function formatValue(value: unknown): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
}

/** 解析字符串为目标类型 */
function parseValue(value: string, type: ConfigItem['type']): unknown {
    switch (type) {
        case 'bool':
            return value === 'true';
        case 'int': {
            const num = parseInt(value, 10);
            if (isNaN(num)) throw new Error('请输入有效的整数');
            return num;
        }
        case 'float': {
            const num = parseFloat(value);
            if (isNaN(num)) throw new Error('请输入有效的数字');
            return num;
        }
        case 'list':
        case 'dict': {
            try {
                return JSON.parse(value);
            } catch {
                throw new Error('请输入有效的 JSON 格式');
            }
        }
        default:
            return value;
    }
}

export default ConfigEditor;
