/**
 * 配置 API 服务
 * 
 * 模块名称: config
 * 主要功能: 提供通用配置管理接口，支持读取和更新各类配置
 */

import { apiClient } from './axios';

// ==================== 类型定义 ====================

/** 配置项 */
export interface ConfigItem {
    key: string;
    value: unknown;
    type: 'str' | 'int' | 'float' | 'bool' | 'list' | 'dict';
    title: string;
    description: string;
    is_secret?: boolean;
    placeholder?: string;
    is_textarea?: boolean;
    overridable?: boolean;
    required?: boolean;
    enum?: string[];
    // UI 渲染元数据
    ref_model_groups?: boolean;
    model_type?: string;
    enable_toggle?: string;
    is_need_restart?: boolean;
    sub_item_name?: string;
}

/** 模型组配置 */
export interface ModelGroupConfig {
    provider: string;
    model: string;
    base_url: string;
    api_key: string;
    model_type?: string;
    temperature?: number | null;
    top_p?: number | null;
    presence_penalty?: number | null;
    frequency_penalty?: number | null;
    extra_body?: string | null;
    enable_vision?: boolean;
    enable_cot?: boolean;
}

/** 模型类型定义 */
export interface ModelType {
    value: string;
    label: string;
    icon?: string;
    description?: string;
    color?: string;
}

/** 全部配置响应 */
export interface AllConfigsResponse {
    status: string;
    data: {
        ai: ConfigItem[];
        server: ConfigItem[];
        database: ConfigItem[];
        security: ConfigItem[];
        agent: ConfigItem[];
    };
}

/** 单分组配置响应 */
export interface ConfigListResponse {
    status: string;
    data: ConfigItem[];
}

// ==================== API 函数 ====================

/**
 * 获取所有配置列表
 */
export async function getAllConfigs(): Promise<AllConfigsResponse['data']> {
    const response = await apiClient.get<AllConfigsResponse>('/config/list');
    return response.data.data;
}

/**
 * 获取 AI 配置列表
 */
export async function getAIConfigList(): Promise<ConfigItem[]> {
    const response = await apiClient.get<ConfigListResponse>('/config/ai');
    return response.data.data;
}

/**
 * 获取 Agent 配置列表
 */
export async function getAgentConfigList(): Promise<ConfigItem[]> {
    const response = await apiClient.get<ConfigListResponse>('/config/agent');
    return response.data.data;
}

/**
 * 更新单个配置项
 */
export async function updateConfigItem(
    group: string,
    key: string,
    value: unknown
): Promise<void> {
    await apiClient.put(`/config/${group}/${key}`, { value });
}

// 导出 configApi 对象
export const configApi = {
    getAllConfigs,
    getAIConfigList,
    getAgentConfigList,
    updateConfigItem,

    // 模型组 API
    getModelGroups: async (): Promise<Record<string, ModelGroupConfig>> => {
        const response = await apiClient.get<Record<string, ModelGroupConfig>>('/config/models');
        return response.data;
    },
    updateModelGroup: async (name: string, config: ModelGroupConfig): Promise<void> => {
        await apiClient.post('/config/models', { name, config });
    },
    deleteModelGroup: async (name: string): Promise<void> => {
        await apiClient.delete(`/config/models/${encodeURIComponent(name)}`);
    },
    getModelTypes: async (): Promise<ModelType[]> => {
        const response = await apiClient.get<ModelType[]>('/config/models/types');
        return response.data;
    },
};

