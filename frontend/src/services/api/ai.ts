import { apiClient } from './axios';
import { config } from '../../config/env';
import { translate } from '../../i18n';
import type { DiagramBundle } from '../../types';

export type DiagramGenerationMode = 'llm' | 'deterministic_seed' | 'heuristic_patch';

export interface AIGenerateResponse {
    status: string;
    response: string;
    run_id: number;
    elements_created: string[];
    tools_used: string[];
    generation_mode?: DiagramGenerationMode;
    request_id?: string;
    idempotency_key?: string;
    code?: string;
    sources?: Array<{
        type: string;
        provider?: string;
        model?: string;
        role?: string;
    }>;
    change_reasoning?: Array<{
        step: string;
        explanation: string;
    }>;
    affected_node_ids?: string[];
    risk_notes?: string[];
}

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

export interface ToolInfo {
    name: string;
    description: string;
    category: string;
    requires_room: boolean;
    dangerous: boolean;
    enabled: boolean;
}

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

export interface MermaidGenerateResponse {
    code: string;
    status: string;
}

export interface ConversationMessage {
    role: 'user' | 'assistant';
    content: string;
    created_at: number;
    extra_data?: Record<string, unknown>;
}

export interface ConversationMessagesResponse {
    messages: ConversationMessage[];
    total: number;
}

export const aiApi = {
    generateShapes: async (
        prompt: string,
        roomId: string,
        options: {
            theme?: string;
            request_id?: string;
            idempotency_key?: string;
            timeout_ms?: number;
            explain?: boolean;
        } = {},
    ): Promise<AIGenerateResponse> => {
        const response = await apiClient.post('/ai/generate', {
            prompt,
            room_id: roomId,
            theme: options.theme ?? 'light',
            request_id: options.request_id,
            idempotency_key: options.idempotency_key,
            timeout_ms: options.timeout_ms,
            explain: options.explain ?? false,
        });
        return response.data;
    },

    generateMermaid: async (
        prompt: string,
        options: {
            roomId?: string;
            conversationId?: number | null;
        } = {},
    ): Promise<MermaidGenerateResponse> => {
        const response = await apiClient.post('/ai/mermaid', {
            prompt,
            room_id: options.roomId,
            conversation_id: options.conversationId ?? undefined,
        });
        return response.data;
    },

    getConversationMessages: async (
        roomId: string,
        conversationId: number,
    ): Promise<ConversationMessagesResponse> => {
        const response = await apiClient.get(
            `/ai/conversations/${roomId}/${conversationId}/messages`,
        );
        return response.data;
    },

    getRunDetail: async (runId: number): Promise<AgentRunDetail> => {
        const response = await apiClient.get(`/ai/run/${runId}`);
        return response.data.run;
    },

    getTools: async (): Promise<ToolInfo[]> => {
        const response = await apiClient.get('/ai/tools');
        return response.data.tools;
    },

    getStatus: async (): Promise<AgentStatus> => {
        const response = await apiClient.get('/ai/status');
        return response.data;
    },

    isRoomBusy: async (roomId: string): Promise<boolean> => {
        const response = await apiClient.get(`/ai/status/${roomId}`);
        return response.data.is_busy;
    },

    summarize: async (message: string): Promise<{ title: string }> => {
        try {
            const response = await apiClient.post('/ai/summarize', { message });
            return { title: response.data.title };
        } catch {
            return { title: message.slice(0, 15) + (message.length > 15 ? '...' : '') };
        }
    },
};

interface AIStreamEnvelope {
    request_id?: string;
    idempotency_key?: string;
    client_session_id?: string;
    room_version?: number;
    seq?: number;
}

export interface AIStreamStep extends AIStreamEnvelope {
    type: 'step';
    step_number: number;
    thought: string;
    action: string | null;
    action_input: Record<string, unknown> | null;
    observation: string | null;
    success: boolean;
    latency_ms: number;
}

export interface AIStreamComplete extends AIStreamEnvelope {
    type: 'complete';
    status: string;
    code?: string | null;
    message?: string;
    response: string;
    run_id: number;
    elements_created: string[];
    tools_used: string[];
    virtual_elements?: Record<string, unknown>[];
    diagram_bundle?: DiagramBundle;
    diagram_family?: string;
    generation_mode?: DiagramGenerationMode;
    managed_scope?: string[];
    patch_summary?: string;
    unmanaged_warnings?: string[];
    action?: 'create' | 'update';
    target_diagram_id?: string;
    sources?: Array<{
        type: string;
        provider?: string;
        model?: string;
        role?: string;
    }>;
    change_reasoning?: Array<{
        step: string;
        explanation: string;
    }>;
    affected_node_ids?: string[];
    risk_notes?: string[];
    metrics?: {
        duration_ms?: number;
        iterations?: number;
        [key: string]: unknown;
    };
}

export interface AIStreamError extends AIStreamEnvelope {
    type: 'error';
    code?: string;
    message: string;
}

export interface AIStreamStarted extends AIStreamEnvelope {
    type: 'started';
    room_id: string;
    prompt: string;
    code?: string;
}

export interface AIStreamResume {
    type: 'resume';
    room_id: string;
    room_version: number;
    event_count: number;
    events: Array<AIStreamMessage>;
}

export interface AIStreamReconnectRequired {
    type: 'reconnect_required';
    code: string;
    message: string;
    room_version?: number;
    snapshot_required?: boolean;
}

export interface AIStreamCloseInfo {
    code: number;
    reason: string;
    wasClean: boolean;
    room_version?: number;
    snapshot_required?: boolean;
}

export function getDefaultAIStreamConnectionError(): string {
    return translate('aiStream.connectionError');
}

export function mapAIStreamCloseReason(reason?: string | null): string {
    switch ((reason ?? '').trim()) {
        case 'authentication_required':
        case 'invalid_token':
            return translate('aiStream.closeReason.authenticationRequired');
        case 'room_membership_required':
            return translate('aiStream.closeReason.roomMembershipRequired');
        case 'room_not_found':
            return translate('aiStream.closeReason.roomNotFound');
        case 'AI_CIRCUIT_OPEN':
            return translate('aiStream.closeReason.circuitOpen');
        case 'TXN_ROLLBACK':
            return translate('aiStream.closeReason.txnRollback');
        case 'RECONNECT_REQUIRES_SNAPSHOT':
            return translate('aiStream.closeReason.reconnectRequiresSnapshot');
        default:
            return getDefaultAIStreamConnectionError();
    }
}

export type AIStreamMessage =
    | AIStreamStep
    | AIStreamComplete
    | AIStreamError
    | AIStreamStarted
    | AIStreamResume
    | AIStreamReconnectRequired;

export interface AIStreamCallbacks {
    onStep?: (step: AIStreamStep) => void;
    onComplete?: (result: AIStreamComplete) => void;
    onError?: (error: AIStreamError) => void;
    onStarted?: (data: AIStreamStarted) => void;
    onClose?: (info: AIStreamCloseInfo) => void;
}

export interface AIStreamClientOptions {
    autoReconnect?: boolean;
    roomVersion?: number;
    clientSessionId?: string;
    reconnectInitialDelayMs?: number;
    reconnectMaxDelayMs?: number;
}

export interface AIStreamRequestOptions {
    theme?: string;
    virtual_mode?: boolean;
    mode?: string;
    conversation_id?: number;
    target_diagram_id?: string;
    target_semantic_id?: string;
    edit_scope?: 'create_new' | 'diagram' | 'semantic';
    request_id?: string;
    idempotency_key?: string;
    timeout_ms?: number;
    explain?: boolean;
}

export class AIStreamClient {
    private ws: WebSocket | null = null;
    private roomId: string;
    private callbacks: AIStreamCallbacks;
    private options: {
        autoReconnect: boolean;
        roomVersion?: number;
        clientSessionId: string;
        reconnectInitialDelayMs: number;
        reconnectMaxDelayMs: number;
    };
    private reconnectDelayMs = 500;
    private closingByCaller = false;
    private connectResolve: (() => void) | null = null;
    private connectReject: ((message: Error) => void) | null = null;
    private opened = false;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private lastSeq = 0;
    private roomVersion?: number;
    private snapshotRequired = false;

    constructor(roomId: string, callbacks: AIStreamCallbacks = {}, options: AIStreamClientOptions = {}) {
        this.roomId = roomId;
        this.callbacks = callbacks;
        const clientSessionId = options.clientSessionId ?? `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        this.options = {
            autoReconnect: options.autoReconnect ?? false,
            roomVersion: options.roomVersion,
            clientSessionId,
            reconnectInitialDelayMs: options.reconnectInitialDelayMs ?? 500,
            reconnectMaxDelayMs: options.reconnectMaxDelayMs ?? 15000,
        };
        this.roomVersion = this.options.roomVersion;
        this.reconnectDelayMs = this.options.reconnectInitialDelayMs;
    }

    connect(): Promise<void> {
        return this._connect(false);
    }

    private _connect(isReconnect: boolean): Promise<void> {
        return new Promise((resolve, reject) => {
            const baseUrl = config.wsBaseUrl.replace('/ws', '');
            const params: Array<[string, string]> = [];
            params.push(['client_session_id', this.options.clientSessionId]);
            if (this.lastSeq > 0) {
                params.push(['resume_from_seq', String(this.lastSeq)]);
            }
            if (this.roomVersion != null) {
                params.push(['room_version', String(this.roomVersion)]);
            }
            const query = params
                .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
                .join('&');
            const wsUrl = `${baseUrl}/api/ai/stream/${encodeURIComponent(this.roomId)}?${query}`;
            console.log('[AI Stream] Connecting:', wsUrl);

            if (!isReconnect) {
                this.opened = false;
                this.snapshotRequired = false;
                this.connectResolve = resolve;
                this.connectReject = reject;
            }

            let settled = false;
            const resolveOnce = () => {
                if (settled) {
                    return;
                }
                settled = true;
                if (this.connectResolve) {
                    this.connectResolve();
                }
                this.connectResolve = null;
                this.connectReject = null;
            };

            const rejectOnce = (message: string) => {
                if (settled) {
                    return;
                }
                settled = true;
                this.ws = null;
                if (this.connectReject) {
                    this.connectReject(new Error(message));
                }
                this.connectResolve = null;
                this.connectReject = null;
            };

            try {
                this.ws = new WebSocket(wsUrl);
            } catch (error) {
                console.error('[AI Stream] Failed to create websocket:', error);
                rejectOnce(getDefaultAIStreamConnectionError());
                return;
            }

            this.ws.onopen = () => {
                this.opened = true;
                this.reconnectDelayMs = this.options.reconnectInitialDelayMs;
                this.reconnectTimer = null;
                console.log('[AI Stream] Connected');
                resolveOnce();
            };

            this.ws.onerror = (error) => {
                console.error('[AI Stream] Connection error:', error);
            };

            this.ws.onclose = (event) => {
                const reason = (event.reason ?? '').trim();
                const closeInfo: AIStreamCloseInfo = {
                    code: event.code,
                    reason,
                    wasClean: event.wasClean,
                    room_version: this.roomVersion,
                    snapshot_required: this.snapshotRequired,
                };
                console.log('[AI Stream] Closed', closeInfo);
                this.ws = null;

                if (!this.opened) {
                    rejectOnce(mapAIStreamCloseReason(reason));
                    return;
                }

                this.callbacks.onClose?.(closeInfo);

                if (!this.closingByCaller && this.options.autoReconnect && reason !== 'RECONNECT_REQUIRES_SNAPSHOT') {
                    this.scheduleReconnect();
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const message: AIStreamMessage = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('[AI Stream] Failed to parse message:', error);
                }
            };
        });
    }

    private scheduleReconnect(): void {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }

        const delay = Math.min(this.reconnectDelayMs, this.options.reconnectMaxDelayMs);
        this.reconnectDelayMs = Math.min(
            this.reconnectDelayMs * 2,
            this.options.reconnectMaxDelayMs,
        );

        this.reconnectTimer = setTimeout(async () => {
            try {
                await this._connect(true);
            } catch {
                if (!this.options.autoReconnect) {
                    return;
                }
                // Keep attempting with backoff until connect succeeds.
                this.scheduleReconnect();
            }
        }, delay);
    }

    private handleMessage(message: AIStreamMessage) {
        const messageClientSessionId = (
            message as AIStreamMessage & { client_session_id?: string }
        ).client_session_id;
        if (
            message.type !== 'resume'
            && messageClientSessionId
            && messageClientSessionId !== this.options.clientSessionId
        ) {
            return;
        }

        const seq = (message as AIStreamMessage & { seq?: number }).seq;
        if (typeof seq === 'number' && seq > this.lastSeq) {
            this.lastSeq = seq;
        }

        const roomVersion = (message as AIStreamMessage & { room_version?: number }).room_version;
        if (typeof roomVersion === 'number') {
            this.roomVersion = roomVersion;
            this.options.roomVersion = roomVersion;
        }

        if (message.type === 'resume') {
            message.events.forEach((event) => this.handleMessage(event));
            return;
        }

        switch (message.type) {
            case 'reconnect_required':
                console.log('[AI Stream] Reconnect required:', message.code);
                if (message.code === 'RECONNECT_REQUIRES_SNAPSHOT') {
                    this.snapshotRequired = Boolean(message.snapshot_required);
                    this.lastSeq = 0;
                    this.roomVersion = roomVersion ?? this.roomVersion;
                }
                break;
            case 'started':
                console.log('[AI Stream] Started:', message.prompt);
                this.callbacks.onStarted?.(message);
                break;
            case 'step':
                console.log(`[AI Stream] Step ${message.step_number}:`, message.action);
                this.callbacks.onStep?.(message);
                break;
            case 'complete':
                console.log('[AI Stream] Complete:', message.response?.substring(0, 50));
                this.callbacks.onComplete?.(message);
                break;
            case 'error':
                console.error('[AI Stream] Error:', message.message);
                this.callbacks.onError?.(message);
                break;
        }
    }

    sendRequest(
        prompt: string,
        options?: AIStreamRequestOptions,
    ): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('[AI Stream] WebSocket is not connected');
            return;
        }

        const payload = {
            type: 'request',
            prompt,
            theme: options?.theme ?? 'light',
            virtual_mode: options?.virtual_mode ?? false,
            mode: options?.mode ?? 'agent',
            conversation_id: options?.conversation_id,
            target_diagram_id: options?.target_diagram_id,
            target_semantic_id: options?.target_semantic_id,
            edit_scope: options?.edit_scope,
            request_id: options?.request_id,
            idempotency_key: options?.idempotency_key,
            timeout_ms: options?.timeout_ms,
            explain: options?.explain ?? false,
        };

        this.ws.send(JSON.stringify(payload));
    }

    disconnect(): void {
        this.closingByCaller = true;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    get isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}


