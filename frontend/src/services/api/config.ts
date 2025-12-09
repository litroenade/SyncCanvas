/**
 * 配置 API 服务
 * 
 * 提供通用配置管理接口，支持读取和更新各类配置
 */

import { config } from '../../config/env';

const API_BASE = config.apiBaseUrl;

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
    const response = await fetch(`${API_BASE}/config/list`);
    if (!response.ok) {
        throw new Error(`获取配置失败: ${response.statusText}`);
    }
    const result: AllConfigsResponse = await response.json();
    return result.data;
}

/**
 * 获取 AI 配置列表
 */
export async function getAIConfigList(): Promise<ConfigItem[]> {
    const response = await fetch(`${API_BASE}/config/ai`);
    if (!response.ok) {
        throw new Error(`获取 AI 配置失败: ${response.statusText}`);
    }
    const result: ConfigListResponse = await response.json();
    return result.data;
}

/**
 * 获取 Agent 配置列表
 */
export async function getAgentConfigList(): Promise<ConfigItem[]> {
    const response = await fetch(`${API_BASE}/config/agent`);
    if (!response.ok) {
        throw new Error(`获取 Agent 配置失败: ${response.statusText}`);
    }
    const result: ConfigListResponse = await response.json();
    return result.data;
}

// 导出 configApi 对象
export const configApi = {
    getAllConfigs,
    getAIConfigList,
    getAgentConfigList,
};
