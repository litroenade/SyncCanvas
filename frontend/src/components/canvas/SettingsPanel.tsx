/**
 * 模块名称: SettingsPanel
 * 主要功能: 画布内设置面板，包含模型配置等
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { configApi, ModelGroup, ModelGroupConfig } from '../../services/api/config';
import {
    Cpu,
    Plus,
    Trash2,
    Edit2,
    Check,
    X,
    Eye,
    EyeOff,
    Loader2,
    ChevronDown,
    ChevronRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface SettingsPanelProps {
    isDark?: boolean;
}

const PROVIDERS = [
    { name: 'SiliconFlow', url: 'https://api.siliconflow.cn/v1' },
    { name: 'OpenAI', url: 'https://api.openai.com/v1' },
    { name: 'DeepSeek', url: 'https://api.deepseek.com/v1' },
    { name: 'Kimi', url: 'https://api.moonshot.cn/v1' },
];

export function SettingsPanel({ isDark = false }: SettingsPanelProps) {
    const queryClient = useQueryClient();
    const [expandedSection, setExpandedSection] = useState<string | null>('models');
    const [editingGroup, setEditingGroup] = useState<{ name: string; config: ModelGroupConfig; isNew?: boolean } | null>(null);
    const [showApiKey, setShowApiKey] = useState(false);

    // 查询模型组 (添加缓存避免重复请求)
    const { data: modelGroups = {}, isLoading } = useQuery<Record<string, ModelGroup>>({
        queryKey: ['model-groups'],
        queryFn: configApi.getModelGroups,
        staleTime: 60000, // 1分钟内不重新请求
    });

    // 保存模型组
    const saveMutation = useMutation({
        mutationFn: ({ name, config }: { name: string; config: ModelGroupConfig }) => {
            // 将 ModelGroupConfig 转换为 ModelGroup
            const modelGroup: ModelGroup = {
                name,
                chat_model: config,
            };
            return configApi.updateModelGroup(name, modelGroup);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['model-groups'] });
            setEditingGroup(null);
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
            config: {
                provider: 'openai',
                model: '',
                base_url: 'https://api.openai.com/v1',
                api_key: '',
                enable_vision: true,
                enable_cot: false,
            },
        });
    };

    const handleSave = () => {
        if (!editingGroup?.name.trim()) return;
        saveMutation.mutate({ name: editingGroup.name, config: editingGroup.config });
    };

    const toggleSection = (section: string) => {
        setExpandedSection(expandedSection === section ? null : section);
    };

    return (
        <div className={cn(
            'h-full overflow-auto p-3 text-sm',
            isDark ? 'text-zinc-200' : 'text-zinc-800'
        )}>
            {/* 模型配置区块 */}
            <div className="mb-4">
                <button
                    onClick={() => toggleSection('models')}
                    className={cn(
                        'w-full flex items-center justify-between p-2 rounded-lg mb-2',
                        isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'
                    )}
                >
                    <span className="flex items-center gap-2 font-medium">
                        <Cpu size={16} />
                        模型配置
                    </span>
                    {expandedSection === 'models' ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>

                {expandedSection === 'models' && (
                    <div className="space-y-2 pl-2">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 className="animate-spin" size={20} />
                            </div>
                        ) : (
                            <>
                                {/* 模型组列表 */}
                                {Object.entries(modelGroups).map(([name, group]) => (
                                    <div
                                        key={name}
                                        className={cn(
                                            'p-2 rounded-lg border',
                                            isDark ? 'bg-zinc-800/50 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                        )}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="font-medium">{name}</div>
                                                <div className="text-xs opacity-60">{group.chat_model?.model}</div>
                                            </div>
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={() => setEditingGroup({ name, config: group.chat_model })}
                                                    className="p-1 hover:bg-zinc-600/30 rounded"
                                                >
                                                    <Edit2 size={14} />
                                                </button>
                                                <button
                                                    onClick={() => deleteMutation.mutate(name)}
                                                    className="p-1 hover:bg-red-500/20 text-red-400 rounded"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                {/* 新增按钮 */}
                                <button
                                    onClick={handleNewGroup}
                                    className={cn(
                                        'w-full flex items-center justify-center gap-2 p-2 rounded-lg border-2 border-dashed',
                                        isDark
                                            ? 'border-zinc-700 hover:border-zinc-600 text-zinc-400'
                                            : 'border-zinc-300 hover:border-zinc-400 text-zinc-500'
                                    )}
                                >
                                    <Plus size={16} />
                                    添加模型组
                                </button>
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* 编辑弹窗 */}
            {editingGroup && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/50">
                    <div className={cn(
                        'w-full max-w-md rounded-xl shadow-2xl p-4',
                        isDark ? 'bg-zinc-900' : 'bg-white'
                    )}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold">{editingGroup.name ? '编辑模型组' : '新建模型组'}</h3>
                            <button onClick={() => setEditingGroup(null)} className="p-1">
                                <X size={18} />
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div>
                                <label className="block text-xs mb-1 opacity-70">名称</label>
                                <input
                                    type="text"
                                    value={editingGroup.name}
                                    onChange={(e) => setEditingGroup({ ...editingGroup, name: e.target.value })}
                                    className={cn(
                                        'w-full px-3 py-2 rounded-lg border text-sm',
                                        isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                    )}
                                    placeholder="我的模型"
                                />
                            </div>

                            <div>
                                <label className="block text-xs mb-1 opacity-70">Base URL</label>
                                <select
                                    onChange={(e) => {
                                        if (e.target.value) {
                                            setEditingGroup({
                                                ...editingGroup,
                                                config: { ...editingGroup.config, base_url: e.target.value }
                                            });
                                        }
                                    }}
                                    className={cn(
                                        'w-full px-3 py-2 rounded-lg border text-sm mb-1',
                                        isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                    )}
                                >
                                    <option value="">选择预设...</option>
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
                                    className={cn(
                                        'w-full px-3 py-2 rounded-lg border text-sm font-mono text-xs',
                                        isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                    )}
                                    placeholder="https://api.openai.com/v1"
                                />
                            </div>

                            <div>
                                <label className="block text-xs mb-1 opacity-70">API Key</label>
                                <div className="relative">
                                    <input
                                        type={showApiKey ? 'text' : 'password'}
                                        value={editingGroup.config.api_key}
                                        onChange={(e) => setEditingGroup({
                                            ...editingGroup,
                                            config: { ...editingGroup.config, api_key: e.target.value }
                                        })}
                                        className={cn(
                                            'w-full px-3 py-2 rounded-lg border text-sm font-mono pr-10',
                                            isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                        )}
                                        placeholder="sk-..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowApiKey(!showApiKey)}
                                        className="absolute right-2 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-100"
                                    >
                                        {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs mb-1 opacity-70">模型名称</label>
                                <input
                                    type="text"
                                    value={editingGroup.config.model}
                                    onChange={(e) => setEditingGroup({
                                        ...editingGroup,
                                        config: { ...editingGroup.config, model: e.target.value }
                                    })}
                                    className={cn(
                                        'w-full px-3 py-2 rounded-lg border text-sm font-mono',
                                        isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                                    )}
                                    placeholder="gpt-4"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-2 mt-4">
                            <button
                                onClick={() => setEditingGroup(null)}
                                className="px-4 py-2 rounded-lg text-sm opacity-70 hover:opacity-100"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saveMutation.isPending}
                                className={cn(
                                    'px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2',
                                    isDark ? 'bg-white text-black' : 'bg-black text-white'
                                )}
                            >
                                {saveMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                保存
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
