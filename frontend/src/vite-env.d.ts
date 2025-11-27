/**
 * Vite 环境变量类型声明
 * 
 * 模块名称: vite-env
 * 主要功能: 为 Vite 提供环境变量的 TypeScript 类型定义
 * 
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
