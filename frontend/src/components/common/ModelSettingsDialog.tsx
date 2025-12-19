/**
 * 模块名称: ModelSettingsDialog
 * 主要功能: 模型配置浮动弹窗 - 支持模型组管理
 * 
 * 模型组结构:
 * - name: 组名称
 * - chat_model: 对话模型 (必填)
 * - vision_model: 视觉模型 (可选)
 * - embedding_model: 嵌入模型 (可选)
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { configApi, ModelGroup, ModelConfig } from '../../services/api/config';
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
    MessageSquare,
    Image,
    Database,
    ChevronDown,
    RefreshCw,
    AlertCircle
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ModelSettingsDialogProps {
    open: boolean;
    onClose: () => void;
    isDark?: boolean;
}

// 预设供应商列表
const PROVIDERS = [
    { name: 'OpenAI', url: 'https://api.openai.com/v1' },
    { name: 'SiliconFlow', url: 'https://api.siliconflow.cn/v1' },
    { name: '火山引擎', url: 'https://ark.cn-beijing.volces.com/api/v3' },
    { name: '阿里通义', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
    { name: 'Gemini', url: 'https://generativelanguage.googleapis.com/v1beta/openai' },
    { name: 'DeepSeek', url: 'https://api.deepseek.com/v1' },
];

// 空模型配置
const emptyModelConfig: ModelConfig = {
    provider: 'openai',
    model: '',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    enable_vision: true,
    enable_cot: false,
};

// 模型类型配置
const MODEL_SLOTS = [
    { key: 'chat_model' as const, label: '对话模型', icon: MessageSquare, color: 'text-blue-400', required: true },
    { key: 'vision_model' as const, label: '视觉模型', icon: Image, color: 'text-purple-400', required: false },
    { key: 'embedding_model' as const, label: '嵌入模型', icon: Database, color: 'text-green-400', required: false },
];

type ModelSlotKey = 'chat_model' | 'vision_model' | 'embedding_model';

interface EditingGroup {
    name: string;
    isNew: boolean;
    chat_model: ModelConfig;
    vision_model: ModelConfig | null;
    embedding_model: ModelConfig | null;
}

export function ModelSettingsDialog({ open, onClose, isDark = false }: ModelSettingsDialogProps) {
    const queryClient = useQueryClient();
    const [editingGroup, setEditingGroup] = useState<EditingGroup | null>(null);
    const [activeSlot, setActiveSlot] = useState<ModelSlotKey>('chat_model');
    const [showApiKey, setShowApiKey] = useState(false);

    // 查询模型组
    const { data: modelGroups = {}, isLoading } = useQuery<Record<string, ModelGroup>>({
        queryKey: ['model-groups'],
        queryFn: configApi.getModelGroups,
        enabled: open,
        staleTime: 60000,
    });

    // 查询当前选中的模型组
    const { data: currentModels } = useQuery({
        queryKey: ['current-models'],
        queryFn: configApi.getCurrentModels,
        enabled: open,
        staleTime: 30000,
    });

    // 切换模型组
    const switchMutation = useMutation({
        mutationFn: (groupName: string) => configApi.switchModelGroup(groupName),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['current-models'] });
        },
    });

    // 保存模型组
    const saveMutation = useMutation({
        mutationFn: ({ name, group }: { name: string; group: ModelGroup }) =>
            configApi.updateModelGroup(name, group),
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
            chat_model: { ...emptyModelConfig },
            vision_model: null,
            embedding_model: null,
        });
        setActiveSlot('chat_model');
    };

    const handleEditGroup = (name: string, group: ModelGroup) => {
        setEditingGroup({
            name,
            isNew: false,
            chat_model: { ...group.chat_model },
            vision_model: group.vision_model ? { ...group.vision_model } : null,
            embedding_model: group.embedding_model ? { ...group.embedding_model } : null,
        });
        setActiveSlot('chat_model');
    };

    const handleCopyGroup = (name: string, group: ModelGroup) => {
        setEditingGroup({
            name: `${name}_copy`,
            isNew: true,
            chat_model: { ...group.chat_model },
            vision_model: group.vision_model ? { ...group.vision_model } : null,
            embedding_model: group.embedding_model ? { ...group.embedding_model } : null,
        });
        setActiveSlot('chat_model');
    };

    // 模型列表获取状态
    const [modelList, setModelList] = useState<{ id: string }[]>([]);
    const [fetchingModels, setFetchingModels] = useState(false);
    const [fetchError, setFetchError] = useState('');

    // 获取模型列表
    const fetchModels = async () => {
        if (!editingGroup) return;
        const config = editingGroup[activeSlot];
        if (!config || !config.base_url || !config.api_key) return;

        setFetchingModels(true);
        setFetchError('');
        setModelList([]);

        try {
            let baseUrl = config.base_url.replace(/\/+$/, '');
            let endpoints = [];
            if (baseUrl.endsWith('/v1')) {
                endpoints.push(`${baseUrl}/models`);
            } else {
                endpoints.push(`${baseUrl}/v1/models`);
                endpoints.push(`${baseUrl}/models`);
            }

            let success = false;
            let models: { id: string }[] = [];

            for (const url of endpoints) {
                try {
                    const res = await fetch(url, {
                        headers: {
                            'Authorization': `Bearer ${config.api_key}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (res.ok) {
                        const data = await res.json();
                        if (data.data && Array.isArray(data.data)) {
                            models = data.data;
                            success = true;
                            break;
                        }
                    } else if (res.status === 401) {
                        throw new Error("API Key 无效 (401)");
                    } else if (res.status === 403) {
                        throw new Error("余额不足或无权限 (403)");
                    }
                } catch (e) {
                    // ignore and try next
                    console.warn(`Failed to fetch from ${url}:`, e);
                    if (e instanceof Error && (e.message.includes('401') || e.message.includes('403'))) {
                        setFetchError(e.message);
                        setFetchingModels(false);
                        return; // 明确的认证错误直接停止
                    }
                }
            }

            if (success) {
                setModelList(models);
            } else {
                setFetchError('无法连接到 API 或未找到模型列表');
            }

        } catch (e) {
            setFetchError(e instanceof Error ? e.message : '获取失败');
        } finally {
            setFetchingModels(false);
        }
    };

    // 此前重置状态
    useEffect(() => {
        if (editingGroup) {
            setModelList([]);
            setFetchError('');
        }
    }, [editingGroup, activeSlot]);

    const handleSave = () => {
        if (!editingGroup?.name.trim()) return;

        const group: ModelGroup = {
            name: editingGroup.name,
            chat_model: editingGroup.chat_model,
            vision_model: editingGroup.vision_model,
            embedding_model: editingGroup.embedding_model,
        };

        saveMutation.mutate({ name: editingGroup.name, group });
    };

    const updateActiveSlotConfig = (updates: Partial<ModelConfig>) => {
        if (!editingGroup) return;

        const currentConfig = editingGroup[activeSlot] || { ...emptyModelConfig };
        const newConfig = { ...currentConfig, ...updates };

        setEditingGroup({
            ...editingGroup,
            [activeSlot]: newConfig,
        });
    };

    const toggleSlotEnabled = (slot: ModelSlotKey) => {
        if (!editingGroup || slot === 'chat_model') return; // chat_model 必填

        if (editingGroup[slot]) {
            setEditingGroup({ ...editingGroup, [slot]: null });
        } else {
            setEditingGroup({ ...editingGroup, [slot]: { ...emptyModelConfig } });
        }
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
    const cardBg = isDark ? 'bg-zinc-800/50' : 'bg-zinc-50';

    const groupNames = Object.keys(modelGroups);
    const activeConfig = editingGroup?.[activeSlot] || null;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
            {/* 背景遮罩 */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={() => editingGroup ? setEditingGroup(null) : onClose()}
            />

            {/* 主弹窗 */}
            <div className={cn(
                'relative w-full max-w-4xl max-h-[85vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col',
                bgColor, textColor
            )}>
                {/* 头部 */}
                <div className={cn('flex items-center justify-between p-4 border-b', borderColor)}>
                    <h2 className="text-lg font-semibold">
                        {editingGroup ? (editingGroup.isNew ? '新建模型组' : `编辑: ${editingGroup.name}`) : '模型配置'}
                    </h2>
                    <button onClick={() => editingGroup ? setEditingGroup(null) : onClose()} className="p-2 hover:bg-zinc-500/20 rounded-lg">
                        <X size={20} />
                    </button>
                </div>

                {/* 内容区 */}
                <div className="flex-1 overflow-auto p-4 space-y-6">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin" size={32} />
                        </div>
                    ) : editingGroup ? (
                        /* 编辑表单 */
                        <div className="space-y-4">
                            {/* 组名称 */}
                            <div>
                                <label className="block text-sm mb-1.5 opacity-70">模型组名称</label>
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
                                    placeholder="我的模型组"
                                />
                            </div>

                            {/* 三列模型选择 */}
                            <div className="grid grid-cols-3 gap-3">
                                {MODEL_SLOTS.map(({ key, label, icon: Icon, color, required }) => {
                                    const isActive = activeSlot === key;
                                    const isEnabled = editingGroup[key] !== null;

                                    return (
                                        <button
                                            key={key}
                                            onClick={() => isEnabled && setActiveSlot(key)}
                                            className={cn(
                                                'p-3 rounded-xl border text-left transition-all',
                                                borderColor,
                                                isActive && 'ring-2 ring-blue-500 border-blue-500',
                                                isEnabled ? 'opacity-100' : 'opacity-40',
                                                !isEnabled && 'cursor-default'
                                            )}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                    <Icon size={16} className={color} />
                                                    <span className="text-sm font-medium">{label}</span>
                                                </div>
                                                {!required && (
                                                    <input
                                                        type="checkbox"
                                                        checked={isEnabled}
                                                        onChange={(e) => {
                                                            e.stopPropagation();
                                                            toggleSlotEnabled(key);
                                                        }}
                                                        className="w-4 h-4"
                                                    />
                                                )}
                                            </div>
                                            {isEnabled && editingGroup[key] && (
                                                <div className="text-xs opacity-60 truncate font-mono">
                                                    {editingGroup[key]!.model || '未配置'}
                                                </div>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>

                            {/* 活动槽位配置 */}
                            {activeConfig && (
                                <div className={cn('p-4 rounded-xl border space-y-4', borderColor, cardBg)}>
                                    <div>
                                        <label className="block text-sm mb-1.5 opacity-70">API 地址</label>
                                        <select
                                            value=""
                                            onChange={(e) => {
                                                if (e.target.value) {
                                                    updateActiveSlotConfig({ base_url: e.target.value });
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
                                            value={activeConfig.base_url}
                                            onChange={(e) => updateActiveSlotConfig({ base_url: e.target.value })}
                                            className={cn('w-full px-3 py-2.5 rounded-lg border text-sm font-mono', inputBg, borderColor)}
                                            placeholder="https://api.openai.com/v1"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm mb-1.5 opacity-70">API Key</label>
                                        <div className="relative">
                                            <input
                                                type={showApiKey ? 'text' : 'password'}
                                                value={activeConfig.api_key}
                                                onChange={(e) => updateActiveSlotConfig({ api_key: e.target.value })}
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

                                    {/* 模型名称 (带自动完成) */}
                                    <div className="relative">
                                        <label className="block text-sm mb-1.5 opacity-70">
                                            模型名称
                                            {modelList.length > 0 && (
                                                <span className="ml-2 text-xs opacity-50">
                                                    (已加载 {modelList.length} 个模型)
                                                </span>
                                            )}
                                        </label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                value={activeConfig.model}
                                                onChange={(e) => updateActiveSlotConfig({ model: e.target.value })}
                                                className={cn('w-full px-3 py-2.5 rounded-lg border text-sm font-mono pr-24', inputBg, borderColor)}
                                                placeholder="gpt-4o"
                                                list="model-list-suggestions"
                                            />

                                            {/* 获取模型列表按钮 */}
                                            <button
                                                type="button"
                                                onClick={fetchModels}
                                                disabled={fetchingModels || !activeConfig.base_url || !activeConfig.api_key}
                                                className={cn(
                                                    "absolute right-1 top-1 bottom-1 px-3 rounded text-xs font-medium transition-colors flex items-center gap-1.5",
                                                    isDark ? "hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200" : "hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800",
                                                    (fetchingModels || !activeConfig.base_url || !activeConfig.api_key) && "opacity-50 cursor-not-allowed"
                                                )}
                                                title="测试连接并获取模型列表"
                                            >
                                                {fetchingModels ? (
                                                    <Loader2 size={14} className="animate-spin" />
                                                ) : (
                                                    <RefreshCw size={14} />
                                                )}
                                                {fetchingModels ? '获取中...' : '刷新列表'}
                                            </button>
                                        </div>

                                        {/* 浏览器原生 datalist 实现简单的自动补全 */}
                                        <datalist id="model-list-suggestions">
                                            {modelList.map(model => (
                                                <option key={model.id} value={model.id} />
                                            ))}
                                        </datalist>

                                        {fetchError && (
                                            <div className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                                                <AlertCircle size={12} />
                                                {fetchError}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* 保存按钮 */}
                            <div className="flex justify-end gap-3 pt-4">
                                <button
                                    onClick={() => setEditingGroup(null)}
                                    className="px-4 py-2 rounded-lg text-sm opacity-70 hover:opacity-100"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saveMutation.isPending || !editingGroup.name.trim() || !editingGroup.chat_model.model}
                                    className={cn(
                                        'px-5 py-2 rounded-lg text-sm font-medium flex items-center gap-2',
                                        isDark ? 'bg-white text-black' : 'bg-black text-white',
                                        (saveMutation.isPending || !editingGroup.name.trim() || !editingGroup.chat_model.model) && 'opacity-50 cursor-not-allowed'
                                    )}
                                >
                                    {saveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                    保存
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* 当前模型组选择器 */}
                            <div className={cn('p-4 rounded-xl border', borderColor, cardBg)}>
                                <h3 className="text-sm font-medium mb-3 opacity-70">当前使用的模型组</h3>
                                <div className="relative">
                                    <select
                                        value={currentModels?.current || ''}
                                        onChange={(e) => switchMutation.mutate(e.target.value)}
                                        className={cn(
                                            'w-full px-4 py-3 rounded-lg border text-sm appearance-none pr-10',
                                            inputBg, borderColor,
                                            switchMutation.isPending && 'opacity-50'
                                        )}
                                        disabled={switchMutation.isPending}
                                    >
                                        <option value="">默认配置</option>
                                        {groupNames.map((name) => (
                                            <option key={name} value={name}>{name}</option>
                                        ))}
                                    </select>
                                    <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 opacity-50 pointer-events-none" />
                                </div>
                            </div>

                            {/* 模型组列表 */}
                            <div>
                                <h3 className="text-sm font-medium mb-3 opacity-70">模型组列表</h3>
                                <div className="space-y-3">
                                    {Object.entries(modelGroups).map(([name, group]) => (
                                        <div
                                            key={name}
                                            className={cn(
                                                'p-4 rounded-xl border flex items-center justify-between group',
                                                borderColor, cardBg,
                                                'hover:border-zinc-500 transition-colors'
                                            )}
                                        >
                                            <div className="min-w-0 flex-1">
                                                <div className="font-medium">{name}</div>
                                                <div className="flex gap-4 mt-1 text-xs opacity-60">
                                                    <span className="flex items-center gap-1">
                                                        <MessageSquare size={12} className="text-blue-400" />
                                                        {group.chat_model.model}
                                                    </span>
                                                    {group.vision_model && (
                                                        <span className="flex items-center gap-1">
                                                            <Image size={12} className="text-purple-400" />
                                                            {group.vision_model.model}
                                                        </span>
                                                    )}
                                                    {group.embedding_model && (
                                                        <span className="flex items-center gap-1">
                                                            <Database size={12} className="text-green-400" />
                                                            {group.embedding_model.model}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex gap-1 ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleCopyGroup(name, group)}
                                                    className="p-2 hover:bg-zinc-500/20 rounded-lg"
                                                    title="复制"
                                                >
                                                    <Copy size={16} />
                                                </button>
                                                <button
                                                    onClick={() => handleEditGroup(name, group)}
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
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
