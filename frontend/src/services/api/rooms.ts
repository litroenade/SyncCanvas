import { apiClient } from './axios'
import type { DiagramBundle, DiagramPatch } from '../../types'

export interface Room {
  id: string
  name: string
  owner_id: number | null
  is_public: boolean
  max_users: number
  created_at: number
  has_password: boolean
  member_count: number
  elements_count: number
  total_contributors: number
  last_active_at: number | null
  online_count: number
  is_owner: boolean
}

export interface RoomListResponse {
  rooms: Room[]
  total: number
}

export interface CreateRoomRequest {
  name: string
  password?: string
  is_public?: boolean
  max_users?: number
}

export interface CommitInfo {
  id: number
  hash: string
  parent_id: number | null
  author_id: number | null
  author_name: string
  message: string
  timestamp: number
  size: number
}

export interface HistoryResponse {
  room_id: string
  head_commit_id: number | null
  commits: CommitInfo[]
  pending_changes: number
  total_size: number
}

export interface CreateCommitRequest {
  message: string
  author_name?: string
}

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

export interface ElementChange {
  element_id: string
  action: 'added' | 'removed' | 'modified'
  element_type: string | null
  text: string | null
}

export interface DiagramCommitSummary {
  diagram_id: string
  title: string
  family: string
  managed_state: string
  component_count: number
  connector_count: number
  version: number
}

export interface DiagramChange {
  diagram_id: string
  action: 'added' | 'removed' | 'modified'
  title: string
  family: string
  managed_state: string | null
  component_count: number | null
  connector_count: number | null
}

export interface CommitDiffResponse {
  room_id: string
  from_commit: CommitInfo | null
  to_commit: CommitInfo
  elements_added: number
  elements_removed: number
  elements_modified: number
  changes: ElementChange[]
  diagrams_added: number
  diagrams_removed: number
  diagrams_modified: number
  diagram_changes: DiagramChange[]
  size_diff: number
}

export interface CommitDetailResponse {
  commit: CommitInfo
  elements_count: number
  element_types: Record<string, number>
  diagrams_count: number
  diagram_families: Record<string, number>
  managed_states: Record<string, number>
  diagrams: DiagramCommitSummary[]
}

export interface DiagramListItem {
  diagram_id: string
  title: string
  family: string
  component_count: number
  connector_count: number
}

export const roomsApi = {
  async list(isPublic?: boolean): Promise<RoomListResponse> {
    const params = isPublic !== undefined ? { is_public: isPublic } : {}
    const response = await apiClient.get('/rooms', { params })
    return response.data
  },

  async create(data: CreateRoomRequest): Promise<Room> {
    const response = await apiClient.post('/rooms', data)
    return response.data
  },

  async get(roomId: string): Promise<Room> {
    const response = await apiClient.get(`/rooms/${roomId}`)
    return response.data
  },

  async join(roomId: string, password?: string): Promise<{ status: string; room_id: string }> {
    const response = await apiClient.post(`/rooms/${roomId}/join`, { password })
    return response.data
  },

  async leave(roomId: string): Promise<{ status: string; room_id: string }> {
    const response = await apiClient.post(`/rooms/${roomId}/leave`, {})
    return response.data
  },

  async delete(roomId: string, password?: string): Promise<{ status: string; room_id: string }> {
    const response = await apiClient.delete(`/rooms/${roomId}`, {
      data: password ? { password } : undefined,
    })
    return response.data
  },

  async getInviteLink(roomId: string): Promise<{ room_id: string; invite_url: string }> {
    const response = await apiClient.get(`/rooms/${roomId}/invite`)
    return response.data
  },

  async getMyRooms(): Promise<RoomListResponse> {
    const response = await apiClient.get('/rooms/my/rooms')
    return response.data
  },

  async getHistory(roomId: string): Promise<HistoryResponse> {
    const response = await apiClient.get(`/rooms/${roomId}/history`)
    return response.data
  },

  async createCommit(roomId: string, data: CreateCommitRequest): Promise<CreateCommitResponse> {
    const response = await apiClient.post(`/rooms/${roomId}/commit`, data)
    return response.data
  },

  async checkoutCommit(roomId: string, commitId: number): Promise<{ status: string; commit_id: number; commit_hash: string; message: string }> {
    const response = await apiClient.post(`/rooms/${roomId}/checkout/${commitId}`, {})
    return response.data
  },

  async revertToCommit(roomId: string, commitId: number): Promise<{ status: string; new_commit: CommitInfo; reverted_to: { id: number; hash: string } }> {
    const response = await apiClient.post(`/rooms/${roomId}/revert/${commitId}`, {})
    return response.data
  },

  async getCommitDetail(roomId: string, commitId: number): Promise<CommitDetailResponse> {
    const response = await apiClient.get(`/rooms/${roomId}/commits/${commitId}`)
    return response.data
  },

  async getCommitDiff(roomId: string, commitId: number, baseCommitId?: number): Promise<CommitDiffResponse> {
    const params = baseCommitId !== undefined ? { base_commit_id: baseCommitId } : {}
    const response = await apiClient.get(`/rooms/${roomId}/diff/${commitId}`, { params })
    return response.data
  },

  async getCommitData(roomId: string, commitId: number): Promise<ArrayBuffer> {
    const response = await apiClient.get(`/rooms/${roomId}/commits/${commitId}/data`, {
      responseType: 'arraybuffer',
    })
    return response.data
  },

  async listDiagrams(roomId: string): Promise<{ room_id: string; total: number; diagrams: DiagramListItem[] }> {
    const response = await apiClient.get(`/rooms/${roomId}/diagrams`)
    return response.data
  },

  async getDiagram(roomId: string, diagramId: string): Promise<DiagramBundle> {
    const response = await apiClient.get(`/rooms/${roomId}/diagrams/${diagramId}`)
    return response.data
  },

  async updateDiagram(roomId: string, diagramId: string, payload: { prompt?: string; patch?: Partial<DiagramPatch> }): Promise<DiagramBundle> {
    const response = await apiClient.patch(`/rooms/${roomId}/diagrams/${diagramId}`, payload)
    return response.data
  },

  async rebuildDiagram(roomId: string, diagramId: string): Promise<DiagramBundle> {
    const response = await apiClient.post(`/rooms/${roomId}/diagrams/${diagramId}/rebuild`, {})
    return response.data
  },
}
