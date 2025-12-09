import { useState, useEffect } from 'react';
import { Loader2, Bot, Info } from 'lucide-react';
import { configApi, type ConfigItem } from '../services/api/config';

interface AgentConfigSectionProps {
    onError?: (error: string) => void;
}

/**
 * Agent 配置展示组件
 * 
 * 显示 Agent 默认配置参数，目前为只读展示
 */
export function AgentConfigSection({ onError }: AgentConfigSectionProps) {
    const [configs, setConfigs] = useState<ConfigItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadConfig = async () => {
            try {
                setLoading(true);
                const data = await configApi.getAgentConfigList();
                setConfigs(data);
            } catch (err) {
                onError?.(err instanceof Error ? err.message : '获取 Agent 配置失败');
            } finally {
                setLoading(false);
            }
        };
        loadConfig();
    }, [onError]);

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
                Agent 默认配置
            </h2>
            
            <div className="config-grid">
                {configs.map((item) => (
                    <div key={item.key} className="config-item">
                        <div className="config-header">
                            <span className="config-title">{item.title}</span>
                            {item.description && (
                                <span className="config-tooltip" title={item.description}>
                                    <Info size={14} />
                                </span>
                            )}
                        </div>
                        <div className="config-value">
                            {renderValue(item)}
                        </div>
                    </div>
                ))}
            </div>
            
            <p className="config-note">
                <Info size={14} />
                Agent 配置为运行时默认值，如需修改请编辑配置文件
            </p>
        </section>
    );
}

/**
 * 渲染配置值
 */
function renderValue(item: ConfigItem): string {
    if (item.type === 'bool') {
        return item.value ? '是' : '否';
    }
    if (typeof item.value === 'number') {
        return String(item.value);
    }
    return String(item.value ?? '-');
}

export default AgentConfigSection;
