import axios from 'axios';
import { config } from '../../config/env';

/**
 * AI 生成响应接口
 */
export interface AIGenerateResponse {
    status: string;
    message: string;
    response?: string;
}

/**
 * Agent 运行详情接口
 */
export interface AgentRunDetail {
    run_id: number;
    room_id: string;
    prompt: string;
    model: string;
    status: string;
    message: string;
    created_at: number;
    finished_at: number | null;
    actions: AgentAction[];
}

export interface AgentAction {
    id: number;
    tool: string;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
    created_at: number;
}

/**
 * 获取 Authorization 请求头
 */
const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * 工具信息接口
 */
export interface ToolInfo {
    name: string;
    description: string;
    category: string;
    requires_room: boolean;
    dangerous: boolean;
    enabled: boolean;
}

/**
 * Agent 状态接口
 */
export interface AgentStatus {
    agent: {
        active_rooms: string[];
        active_count: number;
    };
    tools: {
        total: number;
        enabled: number;
        by_category: Record<string, number>;
    };
}

/**
 * AI 服务接口
 */
export const aiApi = {
    /**
     * 调用 AI 生成图形
     * @param prompt - 用户提示词
     * @param roomId - 房间 ID
     * @returns 生成结果
     */
    generateShapes: async (prompt: string, roomId: string): Promise<AIGenerateResponse> => {
        const response = await axios.post(
            `${config.apiBaseUrl}/ai/generate`,
            { prompt, room_id: roomId },
            { headers: getAuthHeaders() }
        );
        return response.data;
    },

    /**
     * 获取 Agent 运行详情
     * @param runId - 运行 ID
     * @returns Agent 运行详情
     */
    getRunDetail: async (runId: number): Promise<AgentRunDetail> => {
        const response = await axios.get(
            `${config.apiBaseUrl}/ai/runs/${runId}`,
            { headers: getAuthHeaders() }
        );
        return response.data.data;
    },

    /**
     * 获取可用工具列表
     * @returns 工具列表
     */
    getTools: async (): Promise<ToolInfo[]> => {
        const response = await axios.get(
            `${config.apiBaseUrl}/ai/tools`,
            { headers: getAuthHeaders() }
        );
        return response.data.tools;
    },

    /**
     * 获取 Agent 系统状态
     * @returns Agent 状态信息
     */
    getStatus: async (): Promise<AgentStatus> => {
        const response = await axios.get(
            `${config.apiBaseUrl}/ai/status`,
            { headers: getAuthHeaders() }
        );
        return response.data;
    },

    /**
     * 检查房间是否正忙
     * @param roomId - 房间 ID
     * @returns 是否正忙
     */
    isRoomBusy: async (roomId: string): Promise<boolean> => {
        const response = await axios.get(
            `${config.apiBaseUrl}/ai/status/${roomId}`,
            { headers: getAuthHeaders() }
        );
        return response.data.is_busy;
    },
};

