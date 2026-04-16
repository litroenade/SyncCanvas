import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Settings as SettingsIcon,
  Key,
  Server,
  RefreshCw,
  Check,
  X,
  Loader2,
} from 'lucide-react';

import { AgentConfigSection } from '../components/AgentConfigSection';
import { useI18n } from '../i18n';
import { getRequestErrorMessage } from '../services/api/axios';
import {
  settingsApi,
  type AIConfig,
  type AIConfigUpdate,
  type ProviderInfo,
  type ModelInfo,
} from '../services/api/settings';
import '../styles/Settings.css';

export default function Settings() {
  const { t } = useI18n();
  const navigate = useNavigate();

  const [config, setConfig] = useState<AIConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [formData, setFormData] = useState<AIConfigUpdate>({});
  const [showApiKey, setShowApiKey] = useState(false);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true);
      const [aiConfig, providerList] = await Promise.all([
        settingsApi.getAIConfig(),
        settingsApi.getProviders(),
      ]);
      setConfig(aiConfig);
      setProviders(providerList);
      setFormData({
        provider: aiConfig.provider,
        model: aiConfig.model,
        base_url: aiConfig.base_url,
        tool_choice: aiConfig.tool_choice,
        max_tool_calls: aiConfig.max_tool_calls,
      });
    } catch (err) {
      setError(
        t('settings.error.loadFailed', {
          message: getRequestErrorMessage(err, t('settings.unknownError')),
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const fetchModels = async () => {
    if (!formData.base_url) {
      setError(t('settings.error.baseUrlRequired'));
      return;
    }

    try {
      setFetchingModels(true);
      setError(null);
      const response = await settingsApi.getModels(formData.base_url, formData.api_key);
      setModels(response.models);
      if (response.models.length > 0) {
        setSuccess(t('settings.fetchModelsSuccess', { count: response.models.length }));
      } else {
        setError(t('settings.fetchModelsEmpty'));
      }
    } catch (err) {
      setError(
        t('settings.error.fetchModelsFailed', {
          message: getRequestErrorMessage(err, t('settings.unknownError')),
        }),
      );
    } finally {
      setFetchingModels(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const updated = await settingsApi.updateAIConfig(formData);
      setConfig(updated);
      setSuccess(t('settings.saveSuccess'));
      setFormData((prev) => ({ ...prev, api_key: undefined }));
    } catch (err) {
      setError(
        t('settings.error.saveFailed', {
          message: getRequestErrorMessage(err, t('settings.unknownError')),
        }),
      );
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  if (loading) {
    return (
      <div className="settings-page">
        <div className="settings-loading">
          <Loader2 className="spin" />
          <span>{t('settings.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <header className="settings-header">
        <button className="back-button" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
          <span>{t('settings.back')}</span>
        </button>
        <h1>
          <SettingsIcon size={24} />
          <span>{t('settings.title')}</span>
        </h1>
      </header>

      <main className="settings-content">
        {error && (
          <div className="settings-alert error">
            <X size={16} />
            <span>{error}</span>
            <button onClick={() => setError(null)} aria-label={t('modal.cancel')}>
              <X size={14} />
            </button>
          </div>
        )}

        {success && (
          <div className="settings-alert success">
            <Check size={16} />
            <span>{success}</span>
          </div>
        )}

        <section className="settings-section">
          <h2>
            <div className="flex items-center gap-2">
              <Server size={20} />
              {t('settings.primarySectionTitle')}
            </div>
          </h2>

          <div className="form-group">
            <label>{t('settings.providerLabel')}</label>
            <input
              type="text"
              value={formData.provider || ''}
              onChange={(event) => setFormData({ ...formData, provider: event.target.value })}
              placeholder={t('settings.providerPlaceholder')}
            />
          </div>

          <div className="form-group">
            <label>{t('settings.baseUrlLabel')}</label>
            <div className="input-with-dropdown">
              <input
                type="text"
                value={formData.base_url || ''}
                onChange={(event) => setFormData({ ...formData, base_url: event.target.value })}
                placeholder={t('settings.baseUrlPlaceholder')}
                list="provider-list"
              />
              <datalist id="provider-list">
                {providers.map((provider) => (
                  <option key={provider.url} value={provider.url}>
                    {provider.name}
                  </option>
                ))}
              </datalist>
            </div>
          </div>

          <div className="form-group">
            <label>{t('settings.apiKeyLabel')}</label>
            <div className="input-with-button">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={formData.api_key || ''}
                onChange={(event) => setFormData({ ...formData, api_key: event.target.value })}
                placeholder={
                  config?.has_api_key
                    ? t('settings.apiKeyConfiguredPlaceholder')
                    : t('settings.apiKeyPlaceholder')
                }
              />
              <button
                type="button"
                className="toggle-visibility"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                <Key size={16} />
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>{t('settings.modelLabel')}</label>
            <div className="input-with-button">
              <input
                type="text"
                value={formData.model || ''}
                onChange={(event) => setFormData({ ...formData, model: event.target.value })}
                placeholder={t('settings.modelPlaceholder')}
                list="model-list"
              />
              <datalist id="model-list">
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.id}
                  </option>
                ))}
              </datalist>
              <button
                type="button"
                className="fetch-models"
                onClick={fetchModels}
                disabled={fetchingModels || !formData.base_url}
              >
                {fetchingModels ? (
                  <Loader2 size={16} className="spin" />
                ) : (
                  <RefreshCw size={16} />
                )}
                <span>{t('settings.fetchModels')}</span>
              </button>
            </div>
          </div>
        </section>

        <section className="settings-section">
          <h2>{t('settings.advancedSectionTitle')}</h2>

          <div className="form-row">
            <div className="form-group">
              <label>{t('settings.toolChoiceLabel')}</label>
              <select
                value={formData.tool_choice || 'auto'}
                onChange={(event) => setFormData({ ...formData, tool_choice: event.target.value })}
              >
                <option value="auto">{t('settings.toolChoice.auto')}</option>
                <option value="required">{t('settings.toolChoice.required')}</option>
                <option value="none">{t('settings.toolChoice.none')}</option>
              </select>
            </div>

            <div className="form-group">
              <label>{t('settings.maxToolCallsLabel')}</label>
              <input
                type="number"
                value={formData.max_tool_calls || 10}
                onChange={(event) => setFormData({ ...formData, max_tool_calls: parseInt(event.target.value, 10) })}
                min={1}
                max={50}
              />
            </div>
          </div>
        </section>

        <div className="settings-actions">
          <button className="save-button" onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={16} className="spin" />
                <span>{t('settings.saving')}</span>
              </>
            ) : (
              <>
                <Check size={16} />
                <span>{t('settings.save')}</span>
              </>
            )}
          </button>
        </div>

        {config && (
          <section className="settings-section">
            <h2>{t('settings.currentStatusTitle')}</h2>
            <div className="status-info">
              <div className="status-item">
                <span className="label">{t('settings.status.provider')}</span>
                <span className="value">{config.provider}</span>
              </div>
              <div className="status-item">
                <span className="label">{t('settings.status.model')}</span>
                <span className="value">{config.model}</span>
              </div>
              <div className="status-item">
                <span className="label">{t('settings.status.baseUrl')}</span>
                <span className="value">{config.base_url}</span>
              </div>
              <div className="status-item">
                <span className="label">{t('settings.status.apiKey')}</span>
                <span className={`value ${config.has_api_key ? 'configured' : 'not-configured'}`}>
                  {config.has_api_key ? t('settings.status.configured') : t('settings.status.notConfigured')}
                </span>
              </div>
            </div>
          </section>
        )}

        <AgentConfigSection onError={(message) => setError(message)} />
      </main>
    </div>
  );
}
