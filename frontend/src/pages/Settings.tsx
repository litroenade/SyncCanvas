import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings as SettingsIcon, Key, Server, RefreshCw, Check, X, Loader2 } from 'lucide-react';
import { settingsApi, type AIConfig, type AIConfigUpdate, type ProviderInfo, type ModelInfo } from '../services/api/settings';
import { AgentConfigSection } from '../components/AgentConfigSection';

import '../styles/Settings.css';

/**
 * AI 设置页面
 */
export default function Settings() {
    const navigate = useNavigate();
    
    // 配置状态
    const [config, setConfig] = useState<AIConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    
    // 表单状态
    const [formData, setFormData] = useState<AIConfigUpdate>({});
    const [showApiKey, setShowApiKey] = useState(false);
    
    // 供应商和模型
    const [providers, setProviders] = useState<ProviderInfo[]>([]);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [fetchingModels, setFetchingModels] = useState(false);
    
    // 加载配置
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
            setError(`加载配置失败: ${err instanceof Error ? err.message : '未知错误'}`);
        } finally {
            setLoading(false);
        }
    }, []);
    
    useEffect(() => {
        loadConfig();
    }, [loadConfig]);
    
    // 获取可用模型
    const fetchModels = async () => {
        if (!formData.base_url) {
            setError('请先填写 API 地址');
            return;
        }
        
        try {
            setFetchingModels(true);
            setError(null);
            const response = await settingsApi.getModels(
                formData.base_url,
                formData.api_key
            );
            setModels(response.models);
            if (response.models.length > 0) {
                setSuccess(`获取到 ${response.models.length} 个可用模型`);
            } else {
                setError('未获取到模型列表，请手动输入模型名称');
            }
        } catch (err) {
            setError(`获取模型失败: ${err instanceof Error ? err.message : '未知错误'}`);
        } finally {
            setFetchingModels(false);
        }
    };
    
    // 保存配置
    const handleSave = async () => {
        try {
            setSaving(true);
            setError(null);
            const updated = await settingsApi.updateAIConfig(formData);
            setConfig(updated);
            setSuccess('配置已保存');
            // 清除 API Key (显示后不再保存)
            setFormData(prev => ({ ...prev, api_key: undefined }));
        } catch (err) {
            setError(`保存失败: ${err instanceof Error ? err.message : '未知错误'}`);
        } finally {
            setSaving(false);
        }
    };
    
    // 自动清除提示
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
                    <span>加载配置中...</span>
                </div>
            </div>
        );
    }
    
    return (
        <div className="settings-page">
            <header className="settings-header">
                <button className="back-button" onClick={() => navigate(-1)}>
                    <ArrowLeft size={20} />
                    <span>返回</span>
                </button>
                <h1>
                    <SettingsIcon size={24} />
                    <span>AI 设置</span>
                </h1>
            </header>
            
            <main className="settings-content">
                {error && (
                    <div className="settings-alert error">
                        <X size={16} />
                        <span>{error}</span>
                        <button onClick={() => setError(null)}>×</button>
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
                        <Server size={20} />
                        主要模型配置
                    </h2>
                    
                    <div className="form-group">
                        <label>提供商</label>
                        <input
                            type="text"
                            value={formData.provider || ''}
                            onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                            placeholder="例如: siliconflow, openai"
                        />
                    </div>
                    
                    <div className="form-group">
                        <label>API 地址</label>
                        <div className="input-with-dropdown">
                            <input
                                type="text"
                                value={formData.base_url || ''}
                                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                                placeholder="https://api.siliconflow.cn/v1"
                                list="provider-list"
                            />
                            <datalist id="provider-list">
                                {providers.map((p) => (
                                    <option key={p.url} value={p.url}>
                                        {p.name}
                                    </option>
                                ))}
                            </datalist>
                        </div>
                    </div>
                    
                    <div className="form-group">
                        <label>API 密钥</label>
                        <div className="input-with-button">
                            <input
                                type={showApiKey ? 'text' : 'password'}
                                value={formData.api_key || ''}
                                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                                placeholder={config?.has_api_key ? '已配置 (留空保持不变)' : '请输入 API Key'}
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
                        <label>模型名称</label>
                        <div className="input-with-button">
                            <input
                                type="text"
                                value={formData.model || ''}
                                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                                placeholder="Qwen/Qwen2.5-14B-Instruct"
                                list="model-list"
                            />
                            <datalist id="model-list">
                                {models.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {m.id}
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
                                <span>获取模型</span>
                            </button>
                        </div>
                    </div>
                </section>
                
                <section className="settings-section">
                    <h2>高级选项</h2>
                    
                    <div className="form-row">
                        <div className="form-group">
                            <label>工具调用模式</label>
                            <select
                                value={formData.tool_choice || 'auto'}
                                onChange={(e) => setFormData({ ...formData, tool_choice: e.target.value })}
                            >
                                <option value="auto">自动 (auto)</option>
                                <option value="required">必须 (required)</option>
                                <option value="none">禁用 (none)</option>
                            </select>
                        </div>
                        
                        <div className="form-group">
                            <label>最大工具调用次数</label>
                            <input
                                type="number"
                                value={formData.max_tool_calls || 10}
                                onChange={(e) => setFormData({ ...formData, max_tool_calls: parseInt(e.target.value) })}
                                min={1}
                                max={50}
                            />
                        </div>
                    </div>
                </section>
                
                <div className="settings-actions">
                    <button
                        className="save-button"
                        onClick={handleSave}
                        disabled={saving}
                    >
                        {saving ? (
                            <>
                                <Loader2 size={16} className="spin" />
                                <span>保存中...</span>
                            </>
                        ) : (
                            <>
                                <Check size={16} />
                                <span>保存配置</span>
                            </>
                        )}
                    </button>
                </div>
                
                {config && (
                    <section className="settings-section">
                        <h2>当前状态</h2>
                        <div className="status-info">
                            <div className="status-item">
                                <span className="label">提供商:</span>
                                <span className="value">{config.provider}</span>
                            </div>
                            <div className="status-item">
                                <span className="label">模型:</span>
                                <span className="value">{config.model}</span>
                            </div>
                            <div className="status-item">
                                <span className="label">API 地址:</span>
                                <span className="value">{config.base_url}</span>
                            </div>
                            <div className="status-item">
                                <span className="label">API Key:</span>
                                <span className={`value ${config.has_api_key ? 'configured' : 'not-configured'}`}>
                                    {config.has_api_key ? '已配置' : '未配置'}
                                </span>
                            </div>
                        </div>
                    </section>
                )}
                
                {/* Agent 配置展示 */}
                <AgentConfigSection onError={(err) => setError(err)} />
            </main>
        </div>
    );
}
