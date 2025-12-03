/**
 * 环境变量配置
 * 
 * 模块名称: env
 * 主要功能: 统一管理环境变量配置
 * 
 */

/**
 * 应用配置对象
 */
export const config = {
  /** API 基础路径 */
  apiBaseUrl: import.meta.env.DEV ? 'http://localhost:8021/api' : '/api',

  /** WebSocket 基础路径 */
  wsBaseUrl: import.meta.env.DEV ? 'ws://localhost:8021/ws' : '/ws',

  /** WebSocket 认证令牌 */
  wsToken: import.meta.env.VITE_WS_TOKEN ?? '',

  /** 是否是开发环境 */
  isDev: import.meta.env.DEV,

  /** 是否是生产环境 */
  isProd: import.meta.env.PROD,
} as const
