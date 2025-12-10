/**
 * 设置 API 服务
 * 
 * 模块名称: settings
 * 主要功能: 提供 AI 配置相关的 API 调用
 */

import { apiClient } from './axios';

/**
 * AI 配置响应
 */
export interface AIConfig {
    provider: string;
    model: string;
    base_url: string;
    has_api_key: boolean;
    tool_choice: string;
    max_tool_calls: number;
    fallback_provider: string;
    fallback_model: string;
    fallback_base_url: string;
    has_fallback_api_key: boolean;
}

/**
 * AI 配置更新请求
 */
export interface AIConfigUpdate {
    provider?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
    tool_choice?: string;
    max_tool_calls?: number;
    fallback_provider?: string;
    fallback_model?: string;
    fallback_base_url?: string;
    fallback_api_key?: string;
}

/**
 * 模型信息
 */
export interface ModelInfo {
    id: string;
    object: string;
    owned_by?: string;
}

/**
 * 模型列表响应
 */
export interface ModelsResponse {
    models: ModelInfo[];
    total: number;
}

/**
 * 供应商信息
 */
export interface ProviderInfo {
    name: string;
    url: string;
}

/**
 * 设置 API
 */
export const settingsApi = {
    /**
     * 获取 AI 配置
     */
    async getAIConfig(): Promise<AIConfig> {
        const response = await apiClient.get<AIConfig>('/settings/ai');
        return response.data;
    },

    /**
     * 更新 AI 配置
     */
    async updateAIConfig(update: AIConfigUpdate): Promise<AIConfig> {
        const response = await apiClient.put<AIConfig>('/settings/ai', update);
        return response.data;
    },

    /**
     * 获取常用供应商
     */
    async getProviders(): Promise<ProviderInfo[]> {
        const response = await apiClient.get<ProviderInfo[]>('/settings/ai/providers');
        return response.data;
    },

    /**
     * 获取可用模型列表
     */
    async getModels(baseUrl?: string, apiKey?: string): Promise<ModelsResponse> {
        const params = new URLSearchParams();
        if (baseUrl) params.append('base_url', baseUrl);
        if (apiKey) params.append('api_key', apiKey);

        const url = params.toString()
            ? `/settings/ai/models?${params}`
            : '/settings/ai/models';

        const response = await apiClient.get<ModelsResponse>(url);
        return response.data;
    },
};
