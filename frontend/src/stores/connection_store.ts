/**
 * 连接状态管理
 * 
 * 模块名称: connection_store
 * 主要功能: 管理 WebSocket 连接状态和在线用户信息
 * 
 */

import { create } from 'zustand'

/** 连接状态枚举 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

/**
 * 连接状态接口
 */
interface ConnectionState {
  /** 详细连接状态 */
  status: ConnectionStatus
  /** WebSocket 是否已连接 (兼容旧代码) */
  isConnected: boolean
  /** 在线用户数 */
  onlineUsers: number
  /** 当前用户ID */
  userId: string | null
  /** 重连次数 */
  reconnectCount: number
  /** 最后连接时间 */
  lastConnectedAt: number | null
  /** 最后断开时间 */
  lastDisconnectedAt: number | null

  /** 设置连接状态 */
  setStatus: (status: ConnectionStatus) => void
  /** 设置连接状态 (兼容) */
  setIsConnected: (connected: boolean) => void
  /** 设置在线用户数 */
  setOnlineUsers: (count: number) => void
  /** 设置用户ID */
  setUserId: (id: string | null) => void
  /** 增加重连计数 */
  incrementReconnect: () => void
  /** 重置重连计数 */
  resetReconnect: () => void
}

/**
 * 创建连接状态 store
 */
export const useConnectionStore = create<ConnectionState>((set, get) => ({
  status: 'disconnected',
  isConnected: false,
  onlineUsers: 0,
  userId: null,
  reconnectCount: 0,
  lastConnectedAt: null,
  lastDisconnectedAt: null,

  setStatus: (status: ConnectionStatus) => {
    const now = Date.now()
    const updates: Partial<ConnectionState> = { status }

    if (status === 'connected') {
      updates.isConnected = true
      updates.lastConnectedAt = now
      updates.reconnectCount = 0
    } else if (status === 'disconnected') {
      updates.isConnected = false
      updates.lastDisconnectedAt = now
    } else if (status === 'reconnecting') {
      updates.isConnected = false
    }

    set(updates)
  },

  setIsConnected: (connected: boolean) => {
    const { setStatus } = get()
    setStatus(connected ? 'connected' : 'disconnected')
  },

  setOnlineUsers: (count: number) => set({ onlineUsers: count }),
  setUserId: (id: string | null) => set({ userId: id }),

  incrementReconnect: () => set(state => ({
    reconnectCount: state.reconnectCount + 1,
    status: 'reconnecting' as ConnectionStatus,
  })),

  resetReconnect: () => set({ reconnectCount: 0 }),
}))

