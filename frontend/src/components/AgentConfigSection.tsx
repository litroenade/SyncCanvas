import { useState, useEffect, useCallback } from 'react';
import { Loader2, Bot, Info } from 'lucide-react';

import { useI18n } from '../i18n';
import { getRequestErrorMessage } from '../services/api/axios';
import { configApi, type ConfigItem } from '../services/api/config';
import { ConfigEditor } from './common/ConfigEditor';

interface AgentConfigSectionProps {
  onError?: (error: string) => void;
  onSuccess?: (message: string) => void;
}

export function AgentConfigSection({ onError, onSuccess }: AgentConfigSectionProps) {
  const { t } = useI18n();
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true);
      const data = await configApi.getAgentConfigList();
      setConfigs(data);
    } catch (err) {
      onError?.(getRequestErrorMessage(err, t('agentConfig.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [onError, t]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleSave = async (key: string, value: unknown) => {
    try {
      await configApi.updateConfigItem('agent', key, value);
      onSuccess?.(t('agentConfig.saveSuccess', { key }));
      await loadConfig();
    } catch (err) {
      throw new Error(getRequestErrorMessage(err, t('agentConfig.saveFailed')));
    }
  };

  if (loading) {
    return (
      <div className="config-loading">
        <Loader2 className="spin" size={20} />
        <span>{t('agentConfig.loading')}</span>
      </div>
    );
  }

  return (
    <section className="settings-section">
      <h2>
        <Bot size={20} />
        {t('agentConfig.title')}
      </h2>

      <ConfigEditor configs={configs} onSave={handleSave} />

      <p className="config-note">
        <Info size={14} />
        {t('agentConfig.note')}
      </p>
    </section>
  );
}

export default AgentConfigSection;
