import { useState, useEffect, useCallback } from 'react';
import { Loader2, Bot, Info } from 'lucide-react';
import { configApi, type ConfigItem } from '../services/api/config';
import { ConfigEditor } from './common/ConfigEditor';

interface AgentConfigSectionProps {
    onError?: (error: string) => void;
    onSuccess?: (message: string) => void;
}

/**
 * Agent 配置区块组件
 * 
 * 使用 ConfigEditor 展示和编辑 Agent 配置
 */
export function AgentConfigSection({ onError, onSuccess }: AgentConfigSectionProps) {
    const [configs, setConfigs] = useState<ConfigItem[]>([]);
    const [loading, setLoading] = useState(true);

    const loadConfig = useCallback(async () => {
        try {
            setLoading(true);
            const data = await configApi.getAgentConfigList();
            setConfigs(data);
        } catch (err) {
            onError?.(err instanceof Error ? err.message : '获取 Agent 配置失败');
        } finally {
            setLoading(false);
        }
    }, [onError]);

    useEffect(() => {
        loadConfig();
    }, [loadConfig]);

    const handleSave = async (key: string, value: unknown) => {
        try {
            await configApi.updateConfigItem('agent', key, value);
            onSuccess?.(`配置项 "${key}" 已保存`);
            // 重新加载配置以获取最新值
            await loadConfig();
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : '保存失败');
        }
    };

    if (loading) {
        return (
            <div className="config-loading">
                <Loader2 className="spin" size={20} />
                <span>加载配置中...</span>
            </div>
        );
    }

    return (
        <section className="settings-section">
            <h2>
                <Bot size={20} />
                Agent 配置
            </h2>

            <ConfigEditor
                configs={configs}
                onSave={handleSave}
            />

            <p className="config-note">
                <Info size={14} />
                点击配置项可编辑，按 Enter 保存，Esc 取消
            </p>
        </section>
    );
}

export default AgentConfigSection;

