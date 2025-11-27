/**
 * 连接状态管理
 * 
 * 模块名称: connection_store
 * 主要功能: 管理 WebSocket 连接状态和在线用户信息
 * 
 */

import { create } from 'zustand'

/**
 * 连接状态接口
 */
interface ConnectionState {
  /** WebSocket 是否已连接 */
  isConnected: boolean
  /** 在线用户数 */
  onlineUsers: number
  /** 当前用户ID */
  userId: string | null
  
  /** 设置连接状态 */
  setIsConnected: (connected: boolean) => void
  /** 设置在线用户数 */
  setOnlineUsers: (count: number) => void
  /** 设置用户ID */
  setUserId: (id: string | null) => void
}

/**
 * 创建连接状态 store
 */
export const useConnectionStore = create<ConnectionState>((set) => ({
  isConnected: false,
  onlineUsers: 0,
  userId: null,
  
  setIsConnected: (connected: boolean) => set({ isConnected: connected }),
  setOnlineUsers: (count: number) => set({ onlineUsers: count }),
  setUserId: (id: string | null) => set({ userId: id }),
}))
