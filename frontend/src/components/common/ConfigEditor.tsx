import { useState, useCallback } from 'react';
import { Eye, EyeOff, Info, Check, X, Loader2 } from 'lucide-react';

import { useI18n } from '../../i18n';
import { type ConfigItem } from '../../services/api/config';
import '../../styles/ConfigEditor.css';

interface ConfigEditorProps {
  configs: ConfigItem[];
  onSave: (key: string, value: unknown) => Promise<void>;
  readOnly?: boolean;
  className?: string;
}

interface FieldState {
  value: string;
  editing: boolean;
  saving: boolean;
  error: string | null;
}

export function ConfigEditor({ configs, onSave, readOnly = false, className = '' }: ConfigEditorProps) {
  const { t } = useI18n();
  const [fieldStates, setFieldStates] = useState<Record<string, FieldState>>({});

  const getFieldState = (key: string, originalValue: unknown): FieldState => {
    return fieldStates[key] ?? {
      value: formatValue(originalValue),
      editing: false,
      saving: false,
      error: null,
    };
  };

  const updateFieldState = useCallback((
    key: string,
    updates: Partial<FieldState>,
    originalValue: unknown = null,
  ) => {
    setFieldStates((prev) => {
      const currentState = prev[key] ?? {
        value: formatValue(originalValue),
        editing: false,
        saving: false,
        error: null,
      };
      return {
        ...prev,
        [key]: { ...currentState, ...updates },
      };
    });
  }, []);

  const startEdit = (key: string, originalValue: unknown) => {
    updateFieldState(
      key,
      {
        value: formatValue(originalValue),
        editing: true,
        error: null,
      },
      originalValue,
    );
  };

  const cancelEdit = (key: string) => {
    setFieldStates((prev) => {
      const nextState = { ...prev };
      delete nextState[key];
      return nextState;
    });
  };

  const saveField = useCallback(async (item: ConfigItem) => {
    const state = fieldStates[item.key];
    if (!state) return;

    let parsedValue: unknown;
    try {
      parsedValue = parseValue(state.value, item.type, t);
    } catch (error) {
      updateFieldState(item.key, { error: (error as Error).message });
      return;
    }

    updateFieldState(item.key, { saving: true, error: null });

    try {
      await onSave(item.key, parsedValue);
      setFieldStates((prev) => {
        const nextState = { ...prev };
        delete nextState[item.key];
        return nextState;
      });
    } catch (error) {
      updateFieldState(item.key, {
        saving: false,
        error: (error as Error).message || t('agentConfig.saveFailed'),
      });
    }
  }, [fieldStates, onSave, t, updateFieldState]);

  return (
    <div className={`config-editor ${className}`}>
      {configs.map((item) => (
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
  const { t } = useI18n();
  const [showSecret, setShowSecret] = useState(false);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !item.is_textarea) {
      onSave();
    } else if (event.key === 'Escape') {
      onCancelEdit();
    }
  };

  const renderInput = () => {
    if (item.enum && item.enum.length > 0) {
      return (
        <select
          value={state.value}
          onChange={(event) => onValueChange(event.target.value)}
          onBlur={onSave}
          disabled={state.saving}
          className="config-select"
        >
          {item.enum.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      );
    }

    if (item.type === 'bool') {
      return (
        <label className="config-toggle">
          <input
            type="checkbox"
            checked={state.value === 'true'}
            onChange={(event) => {
              onValueChange(event.target.checked ? 'true' : 'false');
              setTimeout(onSave, 0);
            }}
            disabled={state.saving}
          />
          <span className="toggle-slider" />
        </label>
      );
    }

    if (item.is_textarea) {
      return (
        <textarea
          value={state.value}
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={item.placeholder}
          disabled={state.saving}
          className="config-textarea"
          rows={4}
        />
      );
    }

    if (item.is_secret) {
      return (
        <div className="config-secret-input">
          <input
            type={showSecret ? 'text' : 'password'}
            value={state.value}
            onChange={(event) => onValueChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={item.placeholder || t('configEditor.secretPlaceholder')}
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

    if (item.type === 'int' || item.type === 'float') {
      return (
        <input
          type="number"
          value={state.value}
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={onSave}
          placeholder={item.placeholder}
          disabled={state.saving}
          step={item.type === 'float' ? '0.1' : '1'}
          className="config-input config-number"
        />
      );
    }

    return (
      <input
        type="text"
        value={state.value}
        onChange={(event) => onValueChange(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={onSave}
        placeholder={item.placeholder}
        disabled={state.saving}
        className="config-input"
      />
    );
  };

  const renderReadOnlyValue = () => {
    if (item.is_secret) {
      return <span className="config-value secret">********</span>;
    }
    if (item.type === 'bool') {
      return (
        <span className={`config-value bool ${item.value ? 'true' : 'false'}`}>
          {item.value ? t('configEditor.bool.true') : t('configEditor.bool.false')}
        </span>
      );
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
                  <button onClick={onSave} className="save-btn" title={t('configEditor.save')}>
                    <Check size={16} />
                  </button>
                  <button onClick={onCancelEdit} className="cancel-btn" title={t('configEditor.cancel')}>
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
            onKeyDown={(event) => event.key === 'Enter' && onStartEdit()}
          >
            {renderReadOnlyValue()}
          </div>
        )}
      </div>

      {state.error && <div className="config-field-error">{state.error}</div>}
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

function parseValue(
  value: string,
  type: ConfigItem['type'],
  t: (key: string) => string,
): unknown {
  switch (type) {
    case 'bool':
      return value === 'true';
    case 'int': {
      const num = parseInt(value, 10);
      if (Number.isNaN(num)) throw new Error(t('configEditor.error.invalidInteger'));
      return num;
    }
    case 'float': {
      const num = parseFloat(value);
      if (Number.isNaN(num)) throw new Error(t('configEditor.error.invalidNumber'));
      return num;
    }
    case 'list':
    case 'dict': {
      try {
        return JSON.parse(value);
      } catch {
        throw new Error(t('configEditor.error.invalidJson'));
      }
    }
    default:
      return value;
  }
}

export default ConfigEditor;
