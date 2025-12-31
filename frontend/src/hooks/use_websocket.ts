/**
 * WebSocket Hook
 * 
 * 模块名称: use_websocket
 * 主要功能: 提供 WebSocket 连接的 React Hook
 * 
 */

import { useEffect, useRef, useCallback } from 'react'
import { WSManager } from '../utils/websocket'
import { useConnectionStore } from '../stores/connection_store'
import type { WSMessage } from '../types'

/**
 * WebSocket Hook 配置接口
 */
interface UseWebSocketOptions {
  /** WebSocket URL */
  url: string
  /** 消息接收回调 */
  onMessage?: (message: WSMessage) => void
  /** 二进制消息回调 */
  onBinaryMessage?: (data: Uint8Array) => void
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 连接成功回调 */
  onOpen?: () => void
  /** 连接关闭回调 */
  onClose?: () => void
}

/**
 * WebSocket Hook
 * 
 * 提供 WebSocket 连接管理功能，与全局连接状态 store 集成
 * 
 * @param options - WebSocket 配置
 * @returns WebSocket 实例和发送消息函数
 */
export function useWebSocket(options: UseWebSocketOptions) {
  const wsRef = useRef<WSManager | null>(null)
  const { setStatus, incrementReconnect } = useConnectionStore()

  // 标记是否是首次连接
  const isFirstConnectRef = useRef(true)

  useEffect(() => {
    // 设置连接中状态
    setStatus('connecting')

    // 创建 WebSocket 管理器
    wsRef.current = new WSManager({
      url: options.url,
      autoReconnect: options.autoReconnect ?? true,
      onOpen: () => {
        setStatus('connected')
        isFirstConnectRef.current = false
        options.onOpen?.()
      },
      onClose: () => {
        // 如果不是首次连接且启用了自动重连，设置为重连中
        if (!isFirstConnectRef.current && (options.autoReconnect ?? true)) {
          incrementReconnect()
        } else {
          setStatus('disconnected')
        }
        options.onClose?.()
      },
      onError: () => {
        // 错误时如果启用了自动重连，会触发重连
        if (!isFirstConnectRef.current && (options.autoReconnect ?? true)) {
          incrementReconnect()
        } else {
          setStatus('disconnected')
        }
      },
      onMessage: options.onMessage,
      onBinaryMessage: options.onBinaryMessage,
    })

    // 组件卸载时关闭连接
    return () => {
      wsRef.current?.close()
      wsRef.current = null
      setStatus('disconnected')
    }
  }, [options.url, options.autoReconnect])

  /**
   * 发送消息
   * 
   * @param message - 要发送的消息
   */
  const sendMessage = useCallback((message: WSMessage) => {
    wsRef.current?.send(message)
  }, [])

  /**
   * 发送二进制消息
   */
  const sendBinary = useCallback((payload: Uint8Array) => {
    wsRef.current?.sendBinary(payload)
  }, [])

  return {
    wsManager: wsRef.current,
    sendMessage,
    sendBinary,
  }
}

