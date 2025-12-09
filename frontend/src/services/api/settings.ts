import axios from 'axios';
import { config } from '../../config/env';

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
 * 获取 Authorization 请求头
 */
const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * 设置 API
 */
export const settingsApi = {
    /**
     * 获取 AI 配置
     */
    async getAIConfig(): Promise<AIConfig> {
        const response = await axios.get<AIConfig>(
            `${config.apiBaseUrl}/settings/ai`,
            { headers: getAuthHeaders() }
        );
        return response.data;
    },

    /**
     * 更新 AI 配置
     */
    async updateAIConfig(update: AIConfigUpdate): Promise<AIConfig> {
        const response = await axios.put<AIConfig>(
            `${config.apiBaseUrl}/settings/ai`,
            update,
            { headers: getAuthHeaders() }
        );
        return response.data;
    },

    /**
     * 获取常用供应商
     */
    async getProviders(): Promise<ProviderInfo[]> {
        const response = await axios.get<ProviderInfo[]>(
            `${config.apiBaseUrl}/settings/ai/providers`,
            { headers: getAuthHeaders() }
        );
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
            ? `${config.apiBaseUrl}/settings/ai/models?${params}`
            : `${config.apiBaseUrl}/settings/ai/models`;
            
        const response = await axios.get<ModelsResponse>(
            url,
            { headers: getAuthHeaders() }
        );
        return response.data;
    },
};
