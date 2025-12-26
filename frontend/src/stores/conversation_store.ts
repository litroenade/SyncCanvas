import { create } from 'zustand';

/**
 * 对话信息
 */
export interface ConversationInfo {
    id: number;
    room_id: string;
    title: string;
    mode: 'agent' | 'planning' | 'mermaid';
    is_active: boolean;
    message_count: number;
    created_at: number;
    updated_at: number;
}

/**
 * 对话消息
 */
export interface ConversationMessage {
    role: 'user' | 'assistant';
    content: string;
    extra_data?: Record<string, unknown>;
}

/**
 * 对话历史 Store
 */
interface ConversationStore {
    /** 当前房间 ID */
    roomId: string | null;
    /** 对话列表 */
    conversations: ConversationInfo[];
    /** 当前活跃对话 ID */
    activeConversationId: number | null;
    /** 加载状态 */
    isLoading: boolean;
    /** 历史面板是否打开 */
    isHistoryOpen: boolean;

    // Actions
    setRoomId: (roomId: string) => void;
    fetchConversations: () => Promise<void>;
    createConversation: (title?: string, mode?: string) => Promise<number | null>;
    selectConversation: (id: number) => void;
    deleteConversation: (id: number) => Promise<void>;
    updateTitle: (id: number, title: string) => Promise<void>;
    toggleHistory: () => void;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
    roomId: null,
    conversations: [],
    activeConversationId: null,
    isLoading: false,
    isHistoryOpen: false,

    setRoomId: (roomId: string) => {
        set({ roomId, conversations: [], activeConversationId: null });
        get().fetchConversations();
    },

    fetchConversations: async () => {
        const { roomId } = get();
        if (!roomId) return;

        set({ isLoading: true });
        try {
            const response = await fetch(`/api/ai/conversations/${roomId}`);
            const data = await response.json();
            const conversations = data.conversations || [];

            // 找到活跃对话
            const active = conversations.find((c: ConversationInfo) => c.is_active);

            set({
                conversations,
                activeConversationId: active?.id || null,
                isLoading: false,
            });
        } catch (error) {
            console.error('Failed to fetch conversations:', error);
            set({ isLoading: false });
        }
    },

    createConversation: async (title = '新对话', mode = 'planning') => {
        const { roomId } = get();
        if (!roomId) return null;

        try {
            const response = await fetch(`/api/ai/conversations/${roomId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, mode }),
            });
            const data = await response.json();

            await get().fetchConversations();
            return data.conversation_id;
        } catch (error) {
            console.error('Failed to create conversation:', error);
            return null;
        }
    },

    selectConversation: (id: number) => {
        set({ activeConversationId: id });
    },

    deleteConversation: async (id: number) => {
        const { roomId } = get();
        if (!roomId) return;

        try {
            await fetch(`/api/ai/conversations/${roomId}/${id}`, {
                method: 'DELETE',
            });
            await get().fetchConversations();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    },

    updateTitle: async (id: number, title: string) => {
        const { roomId } = get();
        if (!roomId) return;

        try {
            await fetch(`/api/ai/conversations/${roomId}/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title }),
            });

            set((state) => ({
                conversations: state.conversations.map((c) =>
                    c.id === id ? { ...c, title } : c
                ),
            }));
        } catch (error) {
            console.error('Failed to update title:', error);
        }
    },

    toggleHistory: () => {
        set((state) => ({ isHistoryOpen: !state.isHistoryOpen }));
    },
}));
