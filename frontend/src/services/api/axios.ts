/**
 * 模块名称: axios
 * 主要功能: 统一配置的 axios 实例和拦截器
 * 
 * 提供：
 * - 统一的请求配置（baseURL、timeout、headers）
 * - 自动添加 Authorization 请求头
 * - 统一的响应错误处理（401 自动跳转登录）
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { config } from '../../config/env';

/**
 * API 错误响应接口
 */
export interface ApiError {
    status: number;
    message: string;
    detail?: string;
}

/**
 * 创建统一配置的 axios 实例
 * 
 * 所有 API 调用应该使用此实例，而非直接使用 axios
 */
export const apiClient: AxiosInstance = axios.create({
    baseURL: config.apiBaseUrl,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * 请求拦截器：自动添加 Authorization 请求头
 */
apiClient.interceptors.request.use(
    (requestConfig: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('token');
        if (token && requestConfig.headers) {
            requestConfig.headers.Authorization = `Bearer ${token}`;
        }
        return requestConfig;
    },
    (error: AxiosError) => {
        console.error('[API] 请求配置错误:', error);
        return Promise.reject(error);
    }
);

/**
 * 响应拦截器：统一错误处理
 */
apiClient.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError<ApiError>) => {
        const status = error.response?.status;
        const message = error.response?.data?.message || error.message;

        // 401 未授权：清除 token 并跳转登录页
        if (status === 401) {
            console.warn('[API] 认证失败，跳转登录页');
            localStorage.removeItem('token');
            localStorage.removeItem('isGuest');
            // 避免在登录页重复跳转
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login';
            }
        }

        // 403 禁止访问
        if (status === 403) {
            console.error('[API] 权限不足:', message);
        }

        // 500+ 服务器错误
        if (status && status >= 500) {
            console.error('[API] 服务器错误:', message);
        }

        return Promise.reject(error);
    }
);

/**
 * 获取 Authorization 请求头（兼容旧代码，建议迁移到 apiClient）
 * 
 * @deprecated 请使用 apiClient 实例，无需手动添加 headers
 */
export const getAuthHeaders = (): Record<string, string> => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};
