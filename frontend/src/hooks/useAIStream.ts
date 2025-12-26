/**
 * useAIStream Hook
 * 
 * 提供 AI WebSocket 流式交互功能，支持实时步骤反馈
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import {
    AIStreamClient,
    AIStreamStep,
    AIStreamComplete,
    AIStreamError,
    AIStreamStarted,
} from '../services/api/ai';

export interface UseAIStreamOptions {
    roomId: string;
    /** 是否自动连接 */
    autoConnect?: boolean;
}

export interface AIStreamState {
    /** 是否已连接 */
    isConnected: boolean;
    /** 是否正在加载 */
    isLoading: boolean;
    /** 当前步骤列表 */
    steps: AIStreamStep[];
    /** 最终响应 */
    response: string | null;
    /** 错误信息 */
    error: string | null;
    /** 创建的元素 ID 列表 */
    elementsCreated: string[];
    /** 虚拟模式下返回的元素数据 */
    virtualElements: Record<string, unknown>[];
}

export interface UseAIStreamReturn extends AIStreamState {
    /** 连接 WebSocket */
    connect: () => Promise<void>;
    /** 断开连接 */
    disconnect: () => void;
    /** 发送请求 */
    sendRequest: (prompt: string, options?: {
        theme?: string;
        virtual_mode?: boolean;
        mode?: 'agent' | 'planning' | 'mermaid';
    }) => Promise<void>;
    /** 重置状态 */
    reset: () => void;
}

/**
 * AI 流式交互 Hook
 */
export function useAIStream({ roomId, autoConnect = false }: UseAIStreamOptions): UseAIStreamReturn {
    const clientRef = useRef<AIStreamClient | null>(null);

    const [state, setState] = useState<AIStreamState>({
        isConnected: false,
        isLoading: false,
        steps: [],
        response: null,
        error: null,
        elementsCreated: [],
        virtualElements: [],
    });

    // 处理步骤消息
    const handleStep = useCallback((step: AIStreamStep) => {
        setState(prev => ({
            ...prev,
            steps: [...prev.steps, step],
        }));
    }, []);

    // 处理完成消息
    const handleComplete = useCallback((result: AIStreamComplete) => {
        setState(prev => ({
            ...prev,
            isLoading: false,
            response: result.response,
            elementsCreated: result.elements_created,
            virtualElements: result.virtual_elements || [],
        }));
    }, []);

    // 处理错误消息
    const handleError = useCallback((error: AIStreamError) => {
        setState(prev => ({
            ...prev,
            isLoading: false,
            error: error.message,
        }));
    }, []);

    // 处理开始消息
    const handleStarted = useCallback((_data: AIStreamStarted) => {
        setState(prev => ({
            ...prev,
            isLoading: true,
            steps: [],
            response: null,
            error: null,
            elementsCreated: [],
        }));
    }, []);

    // 处理连接关闭
    const handleClose = useCallback(() => {
        setState(prev => ({
            ...prev,
            isConnected: false,
        }));
    }, []);

    // 连接
    const connect = useCallback(async () => {
        if (clientRef.current?.isConnected) {
            return;
        }

        const client = new AIStreamClient(roomId, {
            onStep: handleStep,
            onComplete: handleComplete,
            onError: handleError,
            onStarted: handleStarted,
            onClose: handleClose,
        });

        try {
            await client.connect();
            clientRef.current = client;
            setState(prev => ({ ...prev, isConnected: true }));
        } catch (error) {
            console.error('[useAIStream] 连接失败:', error);
            setState(prev => ({
                ...prev,
                error: '连接失败，请重试',
                isConnected: false,
            }));
        }
    }, [roomId, handleStep, handleComplete, handleError, handleStarted, handleClose]);

    // 断开连接
    const disconnect = useCallback(() => {
        clientRef.current?.disconnect();
        clientRef.current = null;
        setState(prev => ({ ...prev, isConnected: false }));
    }, []);

    // 发送请求
    const sendRequest = useCallback(async (prompt: string, options?: {
        theme?: string;
        virtual_mode?: boolean;
        mode?: 'agent' | 'planning' | 'mermaid';
    }) => {
        // 如果未连接，先连接
        if (!clientRef.current?.isConnected) {
            await connect();
        }

        if (!clientRef.current?.isConnected) {
            setState(prev => ({ ...prev, error: '无法连接到服务器' }));
            return;
        }

        // 根据模式调整选项
        const mode = options?.mode || 'agent';
        const adjustedOptions: { theme?: string; virtual_mode?: boolean; mode?: string } = {
            ...options,
            mode,
        };

        // Planning 模式自动启用虚拟模式
        if (mode === 'planning') {
            adjustedOptions.virtual_mode = true;
        }

        // 发送请求（Mermaid 模式的提示词处理由后端统一完成）
        clientRef.current.sendRequest(prompt, adjustedOptions);
    }, [connect]);

    // 重置状态
    const reset = useCallback(() => {
        setState({
            isConnected: clientRef.current?.isConnected ?? false,
            isLoading: false,
            steps: [],
            response: null,
            error: null,
            elementsCreated: [],
            virtualElements: [],
        });
    }, []);

    // 自动连接
    useEffect(() => {
        if (autoConnect) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [autoConnect, connect, disconnect]);

    return {
        ...state,
        connect,
        disconnect,
        sendRequest,
        reset,
    };
}
