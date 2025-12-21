import { apiClient } from './axios';
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
        const response = await apiClient.post('/ai/generate', { prompt, room_id: roomId });
        return response.data;
    },

    /**
     * 获取 Agent 运行详情
     * @param runId - 运行 ID
     * @returns Agent 运行详情
     */
    getRunDetail: async (runId: number): Promise<AgentRunDetail> => {
        const response = await apiClient.get(`/ai/runs/${runId}`);
        return response.data.data;
    },

    /**
     * 获取可用工具列表
     * @returns 工具列表
     */
    getTools: async (): Promise<ToolInfo[]> => {
        const response = await apiClient.get('/ai/tools');
        return response.data.tools;
    },

    /**
     * 获取 Agent 系统状态
     * @returns Agent 状态信息
     */
    getStatus: async (): Promise<AgentStatus> => {
        const response = await apiClient.get('/ai/status');
        return response.data;
    },

    /**
     * 检查房间是否正忙
     * @param roomId - 房间 ID
     * @returns 是否正忙
     */
    isRoomBusy: async (roomId: string): Promise<boolean> => {
        const response = await apiClient.get(`/ai/status/${roomId}`);
        return response.data.is_busy;
    },
};


// ==================== WebSocket 流式 AI ====================

/**
 * AI 流式步骤消息
 */
export interface AIStreamStep {
    type: 'step';
    step_number: number;
    thought: string;
    action: string | null;
    action_input: Record<string, unknown> | null;
    observation: string | null;
    success: boolean;
    latency_ms: number;
}

/**
 * AI 流式完成消息
 */
export interface AIStreamComplete {
    type: 'complete';
    status: string;
    response: string;
    run_id: number;
    elements_created: string[];
    tools_used: string[];
    metrics?: {
        duration_ms?: number;
        iterations?: number;
        [key: string]: unknown;
    };
}

/**
 * AI 流式错误消息
 */
export interface AIStreamError {
    type: 'error';
    message: string;
}

/**
 * AI 流式开始消息
 */
export interface AIStreamStarted {
    type: 'started';
    room_id: string;
    prompt: string;
}

/**
 * AI 流式消息联合类型
 */
export type AIStreamMessage = AIStreamStep | AIStreamComplete | AIStreamError | AIStreamStarted;

/**
 * AI 流式事件回调
 */
export interface AIStreamCallbacks {
    onStep?: (step: AIStreamStep) => void;
    onComplete?: (result: AIStreamComplete) => void;
    onError?: (error: AIStreamError) => void;
    onStarted?: (data: AIStreamStarted) => void;
    onClose?: () => void;
}

/**
 * AI WebSocket 流式客户端
 * 
 * 用于与后端 /ai/stream/{room_id} 端点建立 WebSocket 连接，
 * 接收 Agent 执行的实时步骤反馈。
 */
export class AIStreamClient {
    private ws: WebSocket | null = null;
    private roomId: string;
    private callbacks: AIStreamCallbacks;

    constructor(roomId: string, callbacks: AIStreamCallbacks = {}) {
        this.roomId = roomId;
        this.callbacks = callbacks;
    }

    /**
     * 连接到 AI 流式端点
     */
    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            // 从 wsBaseUrl 构建 AI 流式 WebSocket URL
            // wsBaseUrl: ws://localhost:8000/ws -> ws://localhost:8000/api/ai/stream/{room_id}
            const baseUrl = config.wsBaseUrl.replace('/ws', '');
            const wsUrl = `${baseUrl}/api/ai/stream/${this.roomId}`;
            console.log('[AI Stream] 连接:', wsUrl);

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('[AI Stream] 已连接');
                resolve();
            };

            this.ws.onerror = (error) => {
                console.error('[AI Stream] 连接错误:', error);
                reject(error);
            };

            this.ws.onclose = () => {
                console.log('[AI Stream] 连接关闭');
                this.callbacks.onClose?.();
            };

            this.ws.onmessage = (event) => {
                try {
                    const message: AIStreamMessage = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (e) {
                    console.error('[AI Stream] 解析消息失败:', e);
                }
            };
        });
    }

    /**
     * 处理接收到的消息
     */
    private handleMessage(message: AIStreamMessage) {
        switch (message.type) {
            case 'started':
                console.log('[AI Stream] 开始处理:', message.prompt);
                this.callbacks.onStarted?.(message);
                break;
            case 'step':
                console.log(`[AI Stream] 步骤 ${message.step_number}:`, message.action);
                this.callbacks.onStep?.(message);
                break;
            case 'complete':
                console.log('[AI Stream] 完成:', message.response?.substring(0, 50));
                this.callbacks.onComplete?.(message);
                break;
            case 'error':
                console.error('[AI Stream] 错误:', message.message);
                this.callbacks.onError?.(message);
                break;
        }
    }

    /**
     * 发送请求
     */
    sendRequest(prompt: string, options?: { theme?: string }): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('[AI Stream] WebSocket 未连接');
            return;
        }

        this.ws.send(JSON.stringify({
            type: 'request',
            prompt,
            theme: options?.theme ?? 'light',
        }));
    }

    /**
     * 断开连接
     */
    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * 检查是否已连接
     */
    get isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

