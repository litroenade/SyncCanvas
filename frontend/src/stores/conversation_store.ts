import { create } from 'zustand';

import { apiClient } from '../services/api/axios';

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

export type { ConversationMessage } from '../services/api/ai';

interface ConversationStore {
    roomId: string | null;
    conversations: ConversationInfo[];
    activeConversationId: number | null;
    isLoading: boolean;
    isHistoryOpen: boolean;
    setRoomId: (roomId: string) => void;
    fetchConversations: () => Promise<void>;
    createConversation: (title?: string, mode?: string) => Promise<number | null>;
    selectConversation: (id: number) => Promise<void>;
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
        void get().fetchConversations();
    },

    fetchConversations: async () => {
        const { roomId } = get();
        if (!roomId) return;

        set({ isLoading: true });
        try {
            const response = await apiClient.get(`/ai/conversations/${roomId}`);
            const conversations = response.data.conversations || [];
            const active = conversations.find((conversation: ConversationInfo) => conversation.is_active);

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

    createConversation: async (title = 'New conversation', mode = 'planning') => {
        const { roomId } = get();
        if (!roomId) return null;

        try {
            const response = await apiClient.post(`/ai/conversations/${roomId}`, { title, mode });
            const conversationId = response.data.conversation_id ?? null;
            if (conversationId !== null) {
                set({ activeConversationId: conversationId });
            }
            await get().fetchConversations();
            return conversationId;
        } catch (error) {
            console.error('Failed to create conversation:', error);
            return null;
        }
    },

    selectConversation: async (id: number) => {
        const { roomId } = get();
        if (!roomId) return;

        set((state) => ({
            activeConversationId: id,
            conversations: state.conversations.map((conversation) => ({
                ...conversation,
                is_active: conversation.id === id,
            })),
        }));

        try {
            await apiClient.patch(`/ai/conversations/${roomId}/${id}`, {
                is_active: true,
            });
        } catch (error) {
            console.error('Failed to select conversation:', error);
            await get().fetchConversations();
        }
    },

    deleteConversation: async (id: number) => {
        const { roomId } = get();
        if (!roomId) return;

        try {
            await apiClient.delete(`/ai/conversations/${roomId}/${id}`);
            await get().fetchConversations();
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    },

    updateTitle: async (id: number, title: string) => {
        const { roomId } = get();
        if (!roomId) return;

        try {
            await apiClient.patch(`/ai/conversations/${roomId}/${id}`, { title });
            set((state) => ({
                conversations: state.conversations.map((conversation) =>
                    conversation.id === id ? { ...conversation, title } : conversation,
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
