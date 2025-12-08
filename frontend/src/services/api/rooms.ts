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
  /** 画布元素数量 */
  elements_count: number
  /** 历史贡献者数量 */
  total_contributors: number
  /** 最后活跃时间 */
  last_active_at: number | null
  /** 当前在线人数 */
  online_count: number
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
  async delete(roomId: string, password?: string): Promise<{ status: string; room_id: string }> {
    const response = await axios.delete(`${config.apiBaseUrl}/rooms/${roomId}`, {
      headers: getAuthHeaders(),
      data: password ? { password } : undefined,
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

  /**
   * 获取房间版本历史
   * @param roomId - 房间 ID
   * @returns 历史信息
   */
  async getHistory(roomId: string): Promise<HistoryResponse> {
    const response = await axios.get(`${config.apiBaseUrl}/rooms/${roomId}/history`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * 创建提交
   * @param roomId - 房间 ID
   * @param data - 提交请求数据
   * @returns 创建的提交信息
   */
  async createCommit(roomId: string, data: CreateCommitRequest): Promise<CreateCommitResponse> {
    const response = await axios.post(
      `${config.apiBaseUrl}/rooms/${roomId}/commit`,
      data,
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 检出提交
   * @param roomId - 房间 ID
   * @param commitId - 提交 ID
   * @returns 检出结果
   */
  async checkoutCommit(roomId: string, commitId: number): Promise<{ status: string; commit_id: number; commit_hash: string; message: string }> {
    const response = await axios.post(
      `${config.apiBaseUrl}/rooms/${roomId}/checkout/${commitId}`,
      {},
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 回滚到指定提交
   * @param roomId - 房间 ID
   * @param commitId - 提交 ID
   * @returns 回滚结果
   */
  async revertToCommit(roomId: string, commitId: number): Promise<{ status: string; new_commit: CommitInfo; reverted_to: { id: number; hash: string } }> {
    const response = await axios.post(
      `${config.apiBaseUrl}/rooms/${roomId}/revert/${commitId}`,
      {},
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 获取提交详情
   * @param roomId - 房间 ID
   * @param commitId - 提交 ID
   * @returns 提交详情
   */
  async getCommitDetail(roomId: string, commitId: number): Promise<CommitDetailResponse> {
    const response = await axios.get(
      `${config.apiBaseUrl}/rooms/${roomId}/commits/${commitId}`,
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 获取提交差异
   * @param roomId - 房间 ID
   * @param commitId - 目标提交 ID
   * @param baseCommitId - 基准提交 ID (可选)
   * @returns 差异信息
   */
  async getCommitDiff(roomId: string, commitId: number, baseCommitId?: number): Promise<CommitDiffResponse> {
    const params = baseCommitId !== undefined ? { base_commit_id: baseCommitId } : {}
    const response = await axios.get(
      `${config.apiBaseUrl}/rooms/${roomId}/diff/${commitId}`,
      { params, headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * 获取提交原始数据 (用于预览)
   * @param roomId - 房间 ID
   * @param commitId - 提交 ID
   * @returns 二进制数据
   */
  async getCommitData(roomId: string, commitId: number): Promise<ArrayBuffer> {
    const response = await axios.get(
      `${config.apiBaseUrl}/rooms/${roomId}/commits/${commitId}/data`,
      {
        headers: getAuthHeaders(),
        responseType: 'arraybuffer'
      }
    )
    return response.data
  },
}

/**
 * 提交信息接口
 */
export interface CommitInfo {
  /** 提交 ID */
  id: number
  /** 提交哈希 (7位) */
  hash: string
  /** 父提交 ID */
  parent_id: number | null
  /** 作者 ID */
  author_id: number | null
  /** 作者名称 */
  author_name: string
  /** 提交消息 */
  message: string
  /** 时间戳 (毫秒) */
  timestamp: number
  /** 数据大小 (字节) */
  size: number
}

/**
 * 历史响应接口
 */
export interface HistoryResponse {
  /** 房间 ID */
  room_id: string
  /** 当前 HEAD 指向的提交 ID */
  head_commit_id: number | null
  /** 提交列表 (从新到旧) */
  commits: CommitInfo[]
  /** 待提交的更改数量 */
  pending_changes: number
  /** 总数据大小 */
  total_size: number
}

/**
 * 创建提交请求接口
 */
export interface CreateCommitRequest {
  /** 提交消息 */
  message: string
  /** 作者名称 (可选) */
  author_name?: string
}

/**
 * 创建提交响应接口
 */
export interface CreateCommitResponse {
  status: string
  commit: {
    id: number
    hash: string
    message: string
    author_name: string
    timestamp: number
  }
}

/**
 * 元素变更信息接口
 */
export interface ElementChange {
  /** 元素 ID */
  element_id: string
  /** 变更类型 */
  action: 'added' | 'removed' | 'modified'
  /** 元素类型 */
  element_type: string | null
  /** 文本内容 */
  text: string | null
}

/**
 * Commit 差异响应接口
 */
export interface CommitDiffResponse {
  /** 房间 ID */
  room_id: string
  /** 基准提交 */
  from_commit: CommitInfo | null
  /** 目标提交 */
  to_commit: CommitInfo
  /** 新增元素数 */
  elements_added: number
  /** 删除元素数 */
  elements_removed: number
  /** 修改元素数 */
  elements_modified: number
  /** 变更详情列表 */
  changes: ElementChange[]
  /** 大小差异 (字节) */
  size_diff: number
}

/**
 * Commit 详情响应接口
 */
export interface CommitDetailResponse {
  /** 提交信息 */
  commit: CommitInfo
  /** 元素总数 */
  elements_count: number
  /** 元素类型统计 */
  element_types: Record<string, number>
}