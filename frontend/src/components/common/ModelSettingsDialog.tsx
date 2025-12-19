/**
 * 模块名称: ModelSettingsDialog
 * 主要功能: 模型配置浮动弹窗
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { configApi, ModelGroupConfig } from '../../services/api/config';
import {
    X,
    Plus,
    Trash2,
    Edit2,
    Check,
    Eye,
    EyeOff,
    Loader2,
    Copy,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ModelSettingsDialogProps {
    open: boolean;
    onClose: () => void;
    isDark?: boolean;
}

// 预设供应商列表 (参考 nekro-agent)
const PROVIDERS = [
    // 国内
    { name: 'SiliconFlow', url: 'https://api.siliconflow.cn/v1' },
    { name: 'DeepSeek', url: 'https://api.deepseek.com/v1' },
    { name: 'Kimi (Moonshot)', url: 'https://api.moonshot.cn/v1' },
    { name: '通义千问', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
    { name: '豆包', url: 'https://ark.cn-beijing.volces.com/api/v3' },
    { name: '智谱清言', url: 'https://open.bigmodel.cn/api/paas/v4' },
    { name: '百川', url: 'https://api.baichuan-ai.com/v1' },
    // 国际
    { name: 'OpenAI', url: 'https://api.openai.com/v1' },
    { name: 'Gemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai' },
    { name: 'Groq', url: 'https://api.groq.com/openai/v1' },
];

export function ModelSettingsDialog({ open, onClose, isDark = false }: ModelSettingsDialogProps) {
    const queryClient = useQueryClient();
    const [editingGroup, setEditingGroup] = useState<{ name: string; config: ModelGroupConfig; isNew?: boolean } | null>(null);
    const [showApiKey, setShowApiKey] = useState(false);
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [fetchingModels, setFetchingModels] = useState(false);

    // 获取可用模型列表
    const handleFetchModels = async () => {
        if (!editingGroup?.config.base_url || !editingGroup?.config.api_key) {
            return;
        }
        setFetchingModels(true);
        try {
            const response = await fetch(`/api/config/ai/models?base_url=${encodeURIComponent(editingGroup.config.base_url)}&api_key=${encodeURIComponent(editingGroup.config.api_key)}`);
            if (response.ok) {
                const data = await response.json();
                setAvailableModels(data.models?.map((m: { id: string }) => m.id) || []);
            }
        } catch (e) {
            console.error('获取模型列表失败:', e);
        } finally {
            setFetchingModels(false);
        }
    };


    // 查询模型组
    const { data: modelGroups = {}, isLoading } = useQuery<Record<string, ModelGroupConfig>>({
        queryKey: ['model-groups'],
        queryFn: configApi.getModelGroups,
        enabled: open,
    });

    // 保存模型组
    const saveMutation = useMutation({
        mutationFn: ({ name, config }: { name: string; config: ModelGroupConfig }) =>
            configApi.updateModelGroup(name, config),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['model-groups'] });
            setEditingGroup(null);
        },
        onError: (error: Error) => {
            console.error('保存模型组失败:', error);
            alert(`保存失败: ${error.message}`);
        },
    });

    // 删除模型组
    const deleteMutation = useMutation({
        mutationFn: (name: string) => configApi.deleteModelGroup(name),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['model-groups'] });
        },
    });



    const handleNewGroup = () => {
        setEditingGroup({
            name: '',
            isNew: true,
            config: {
                provider: 'openai',
                model: '',
                base_url: 'https://api.openai.com/v1',
                api_key: '',
                enable_vision: true,
                enable_cot: false,
            },
        });
        setAvailableModels([]);
    };

    const handleEditGroup = (name: string, config: ModelGroupConfig) => {
        setEditingGroup({ name, config: { ...config }, isNew: false });
    };

    const handleCopyGroup = (name: string, config: ModelGroupConfig) => {
        setEditingGroup({
            name: `${name}_copy`,
            config: { ...config },
            isNew: true,
        });
    };

    const handleSave = () => {
        if (!editingGroup?.name.trim()) return;
        saveMutation.mutate({ name: editingGroup.name, config: editingGroup.config });
    };

    // ESC 关闭
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                if (editingGroup) {
                    setEditingGroup(null);
                } else {
                    onClose();
                }
            }
        };
        if (open) {
            window.addEventListener('keydown', handleEsc);
            return () => window.removeEventListener('keydown', handleEsc);
        }
    }, [open, editingGroup, onClose]);

    if (!open) return null;

    const bgColor = isDark ? 'bg-zinc-900' : 'bg-white';
    const borderColor = isDark ? 'border-zinc-700' : 'border-zinc-200';
    const textColor = isDark ? 'text-zinc-100' : 'text-zinc-900';
    const inputBg = isDark ? 'bg-zinc-800' : 'bg-zinc-50';

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
            {/* 背景遮罩 */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={() => editingGroup ? setEditingGroup(null) : onClose()}
            />

            {/* 主弹窗 */}
            <div className={cn(
                'relative w-full max-w-2xl max-h-[85vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col',
                bgColor, textColor
            )}>
                {/* 头部 */}
                <div className={cn('flex items-center justify-between p-4 border-b', borderColor)}>
                    <h2 className="text-lg font-semibold">模型配置</h2>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-500/20 rounded-lg">
                        <X size={20} />
                    </button>
                </div>

                {/* 内容区 */}
                <div className="flex-1 overflow-auto p-4">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin" size={32} />
                        </div>
                    ) : editingGroup ? (
                        /* 编辑表单 */
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm mb-1.5 opacity-70">名称</label>
                                <input
                                    type="text"
                                    value={editingGroup.name}
                                    onChange={(e) => setEditingGroup({ ...editingGroup, name: e.target.value })}
                                    disabled={!editingGroup.isNew}
                                    className={cn(
                                        'w-full px-3 py-2.5 rounded-lg border text-sm',
                                        inputBg, borderColor,
                                        !editingGroup.isNew && 'opacity-60 cursor-not-allowed'
                                    )}
                                    placeholder="我的模型"
                                />
                            </div>

                            <div>
                                <label className="block text-sm mb-1.5 opacity-70">API 地址</label>
                                <select
                                    value=""
                                    onChange={(e) => {
                                        if (e.target.value) {
                                            setEditingGroup({
                                                ...editingGroup,
                                                config: { ...editingGroup.config, base_url: e.target.value }
                                            });
                                        }
                                    }}
                                    className={cn('w-full px-3 py-2.5 rounded-lg border text-sm mb-2', inputBg, borderColor)}
                                >
                                    <option value="">选择预设供应商...</option>
                                    {PROVIDERS.map((p) => (
                                        <option key={p.url} value={p.url}>{p.name}</option>
                                    ))}
                                </select>
                                <input
                                    type="text"
                                    value={editingGroup.config.base_url}
                                    onChange={(e) => setEditingGroup({
                                        ...editingGroup,
                                        config: { ...editingGroup.config, base_url: e.target.value }
                                    })}
                                    className={cn('w-full px-3 py-2.5 rounded-lg border text-sm font-mono', inputBg, borderColor)}
                                    placeholder="https://api.openai.com/v1"
                                />
                            </div>

                            <div>
                                <label className="block text-sm mb-1.5 opacity-70">API Key</label>
                                <div className="relative">
                                    <input
                                        type={showApiKey ? 'text' : 'password'}
                                        value={editingGroup.config.api_key}
                                        onChange={(e) => setEditingGroup({
                                            ...editingGroup,
                                            config: { ...editingGroup.config, api_key: e.target.value }
                                        })}
                                        className={cn('w-full px-3 py-2.5 rounded-lg border text-sm font-mono pr-10', inputBg, borderColor)}
                                        placeholder="sk-..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowApiKey(!showApiKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-100"
                                    >
                                        {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm mb-1.5 opacity-70">模型名称</label>
                                <div className="flex gap-2">
                                    {availableModels.length > 0 ? (
                                        <select
                                            value={editingGroup.config.model}
                                            onChange={(e) => setEditingGroup({
                                                ...editingGroup,
                                                config: { ...editingGroup.config, model: e.target.value }
                                            })}
                                            className={cn('flex-1 px-3 py-2.5 rounded-lg border text-sm font-mono', inputBg, borderColor)}
                                        >
                                            <option value="">选择模型...</option>
                                            {availableModels.map((m) => (
                                                <option key={m} value={m}>{m}</option>
                                            ))}
                                        </select>
                                    ) : (
                                        <input
                                            type="text"
                                            value={editingGroup.config.model}
                                            onChange={(e) => setEditingGroup({
                                                ...editingGroup,
                                                config: { ...editingGroup.config, model: e.target.value }
                                            })}
                                            className={cn('flex-1 px-3 py-2.5 rounded-lg border text-sm font-mono', inputBg, borderColor)}
                                            placeholder="gpt-4o"
                                        />
                                    )}
                                    <button
                                        type="button"
                                        onClick={handleFetchModels}
                                        disabled={fetchingModels || !editingGroup.config.base_url || !editingGroup.config.api_key}
                                        className={cn(
                                            'px-3 py-2.5 rounded-lg border text-sm whitespace-nowrap',
                                            borderColor,
                                            'hover:bg-zinc-500/20 disabled:opacity-50 disabled:cursor-not-allowed'
                                        )}
                                    >
                                        {fetchingModels ? <Loader2 size={16} className="animate-spin" /> : '获取列表'}
                                    </button>
                                </div>
                            </div>


                        </div>
                    ) : (
                        /* 模型组列表 */
                        <div className="space-y-3">
                            {Object.entries(modelGroups).map(([name, config]) => (
                                <div
                                    key={name}
                                    className={cn(
                                        'p-4 rounded-xl border flex items-center justify-between',
                                        borderColor,
                                        isDark ? 'bg-zinc-800/50' : 'bg-zinc-50'
                                    )}
                                >
                                    <div className="min-w-0 flex-1">
                                        <div className="font-medium truncate">{name}</div>
                                        <div className="text-sm opacity-60 truncate font-mono">{config.model}</div>
                                    </div>
                                    <div className="flex gap-1 ml-3">
                                        <button
                                            onClick={() => handleCopyGroup(name, config)}
                                            className="p-2 hover:bg-zinc-500/20 rounded-lg"
                                            title="复制"
                                        >
                                            <Copy size={16} />
                                        </button>
                                        <button
                                            onClick={() => handleEditGroup(name, config)}
                                            className="p-2 hover:bg-zinc-500/20 rounded-lg"
                                            title="编辑"
                                        >
                                            <Edit2 size={16} />
                                        </button>
                                        <button
                                            onClick={() => deleteMutation.mutate(name)}
                                            className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg"
                                            title="删除"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {Object.keys(modelGroups).length === 0 && (
                                <div className="text-center py-8 opacity-50">
                                    暂无模型配置
                                </div>
                            )}

                            <button
                                onClick={handleNewGroup}
                                className={cn(
                                    'w-full p-4 rounded-xl border-2 border-dashed flex items-center justify-center gap-2',
                                    borderColor,
                                    'hover:border-blue-400 hover:text-blue-400 transition-colors'
                                )}
                            >
                                <Plus size={20} />
                                添加模型组
                            </button>
                        </div>
                    )}
                </div>

                {/* 底部按钮 */}
                {editingGroup && (
                    <div className={cn('flex justify-end gap-3 p-4 border-t', borderColor)}>
                        <button
                            onClick={() => setEditingGroup(null)}
                            className="px-4 py-2 rounded-lg text-sm opacity-70 hover:opacity-100"
                        >
                            取消
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saveMutation.isPending || !editingGroup.name.trim()}
                            className={cn(
                                'px-5 py-2 rounded-lg text-sm font-medium flex items-center gap-2',
                                isDark ? 'bg-white text-black' : 'bg-black text-white',
                                (saveMutation.isPending || !editingGroup.name.trim()) && 'opacity-50 cursor-not-allowed'
                            )}
                        >
                            {saveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                            保存
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
