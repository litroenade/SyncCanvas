/**
 * 房间 API 服务
 *
 * 模块名称: rooms
 * 主要功能: 提供房间管理相关的 API 调用
 */

import axios from 'axios'
import { config } from '../../config/env'

/**
 * 房间信息接口
 */
export interface Room {
  /** 房间 ID */
  id: string
  /** 房间名称 */
  name: string
  /** 创建者 ID */
  owner_id: number | null
  /** 是否公开 */
  is_public: boolean
  /** 最大用户数 */
  max_users: number
  /** 创建时间戳 */
  created_at: number
  /** 是否有密码 */
  has_password: boolean
  /** 当前成员数 */
  member_count: number
}

/**
 * 房间列表响应接口
 */
export interface RoomListResponse {
  rooms: Room[]
  total: number
}

/**
 * 创建房间请求接口
 */
export interface CreateRoomRequest {
  name: string
  password?: string
  is_public?: boolean
  max_users?: number
}

/**
 * 获取 Authorization 请求头
 * @returns 包含 Bearer Token 的请求头对象
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * 房间 API 服务对象
 */
export const roomsApi = {
  /**
   * 获取房间列表
   * @param isPublic - 是否只获取公开房间
   * @returns 房间列表响应
   */
  async list(isPublic?: boolean): Promise<RoomListResponse> {
    const params = isPublic !== undefined ? { is_public: isPublic } : {}
    const response = await axios.get(`${config.apiBaseUrl}/rooms`, {
      params,
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 创建房间
   * @param data - 创建房间请求数据
   * @returns 创建的房间信息
   */
  async create(data: CreateRoomRequest): Promise<Room> {
    const response = await axios.post(`${config.apiBaseUrl}/rooms`, data, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 获取房间详情
   * @param roomId - 房间 ID
   * @returns 房间详情
   */
  async get(roomId: string): Promise<Room> {
    const response = await axios.get(`${config.apiBaseUrl}/rooms/${roomId}`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 加入房间
   * @param roomId - 房间 ID
   * @param password - 房间密码 (可选)
   * @returns 加入结果
   */
  async join(roomId: string, password?: string): Promise<{ status: string; room_id: string }> {
    const response = await axios.post(
      `${config.apiBaseUrl}/rooms/${roomId}/join`,
      { password },
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 离开房间
   * @param roomId - 房间 ID
   * @returns 离开结果
   */
  async leave(roomId: string): Promise<{ status: string; room_id: string }> {
    const response = await axios.post(
      `${config.apiBaseUrl}/rooms/${roomId}/leave`,
      {},
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 删除房间
   * @param roomId - 房间 ID
   * @returns 删除结果
   */
  async delete(roomId: string): Promise<{ status: string; room_id: string }> {
    const response = await axios.delete(`${config.apiBaseUrl}/rooms/${roomId}`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 获取邀请链接
   * @param roomId - 房间 ID
   * @returns 邀请链接信息
   */
  async getInviteLink(roomId: string): Promise<{ room_id: string; invite_url: string }> {
    const response = await axios.get(`${config.apiBaseUrl}/rooms/${roomId}/invite`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 获取我加入的房间
   * @returns 房间列表响应
   */
  async getMyRooms(): Promise<RoomListResponse> {
    const response = await axios.get(`${config.apiBaseUrl}/rooms/my/rooms`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },
}
