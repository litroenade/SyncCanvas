/**
 * WebSocket 工具类
 * 
 * 模块名称: websocket
 * 主要功能: 封装 WebSocket 连接管理

 */

import type { WSMessage } from '../types'

/**
 * WebSocket 连接配置接口
 */
interface WSConfig {
  /** WebSocket URL */
  url: string
  /** 连接成功回调 */
  onOpen?: () => void
  /** 连接关闭回调 */
  onClose?: () => void
  /** 错误回调 */
  onError?: (error: Event) => void
  /** 消息接收回调 */
  onMessage?: (message: WSMessage) => void
  /** 二进制消息回调 */
  onBinaryMessage?: (data: Uint8Array) => void
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 重连间隔(毫秒) */
  reconnectInterval?: number
}

/**
 * WebSocket 管理器类
 * 
 * 提供以下功能:
 * - 自动重连
 * - 心跳检测
 * - 消息队列
 * - 连接状态管理
 */
export class WSManager {
  private ws: WebSocket | null = null
  private config: WSConfig
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private messageQueue: Array<{ kind: 'json'; payload: WSMessage } | { kind: 'binary'; payload: Uint8Array }> = []

  /**
   * 创建 WebSocket 管理器
   * 
   * @param config - WebSocket 配置
   */
  constructor(config: WSConfig) {
    this.config = {
      autoReconnect: true,
      reconnectInterval: 3000,
      ...config,
    }
    this.connect()
  }

  /**
   * 建立 WebSocket 连接
   */
  private connect() {
    try {
      this.ws = new WebSocket(this.config.url)

      this.ws.onopen = () => {
        console.log('WebSocket 连接已建立')
        this.config.onOpen?.()
        this.startHeartbeat()
        this.flushMessageQueue()
      }

      this.ws.onclose = () => {
        console.log('WebSocket 连接已关闭')
        this.config.onClose?.()
        this.stopHeartbeat()
        
        if (this.config.autoReconnect) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error)
        this.config.onError?.(error)
      }

      this.ws.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          try {
            const message = JSON.parse(event.data) as WSMessage
            this.config.onMessage?.(message)
          } catch (error) {
            console.error('解析 WebSocket 消息失败:', error)
          }
          return
        }

        // 处理二进制消息 (ArrayBuffer 或 Blob)
        try {
          const buffer = event.data instanceof Blob ? await event.data.arrayBuffer() : event.data
          const binary = new Uint8Array(buffer)
          this.config.onBinaryMessage?.(binary)
        } catch (error) {
          console.error('处理二进制消息失败:', error)
        }
      }
    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error)
      if (this.config.autoReconnect) {
        this.scheduleReconnect()
      }
    }
  }

  /**
   * 发送消息
   * 
   * @param message - 要发送的消息
   */
  send(message: WSMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // 连接未建立时加入队列
      this.messageQueue.push({ kind: 'json', payload: message })
    }
  }

  /**
   * 发送二进制数据
   *
   * @param payload - 要发送的二进制数据
   */
  sendBinary(payload: Uint8Array) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload)
    } else {
      // 连接未建立时暂存，等连接后统一发送
      const bufferCopy = payload.slice()
      this.messageQueue.push({ kind: 'binary', payload: bufferCopy })
    }
  }

  /**
   * 刷新消息队列
   * 在连接建立后发送队列中的所有消息
   */
  private flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const entry = this.messageQueue.shift()
      if (!entry) {
        continue
      }

      if (entry.kind === 'binary') {
        this.sendBinary(entry.payload)
      } else {
        this.send(entry.payload)
      }
    }
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat() {
    this.heartbeatTimer = window.setInterval(() => {
      this.send({ type: 'ping', data: {} })
    }, 30000) // 每30秒发送一次心跳
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 计划重连
   */
  private scheduleReconnect() {
    if (this.reconnectTimer) {
      return
    }

    this.reconnectTimer = window.setTimeout(() => {
      console.log('尝试重新连接 WebSocket...')
      this.reconnectTimer = null
      this.connect()
    }, this.config.reconnectInterval)
  }

  /**
   * 关闭连接
   */
  close() {
    this.config.autoReconnect = false
    this.stopHeartbeat()
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.ws?.close()
    this.ws = null
  }

  /**
   * 获取当前连接状态
   * 
   * @returns 是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
