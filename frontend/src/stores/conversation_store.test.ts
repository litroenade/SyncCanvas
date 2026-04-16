import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';

vi.mock('../services/api/axios', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}));

import { apiClient } from '../services/api/axios';
import { useConversationStore } from './conversation_store';

function resetConversationStore() {
  useConversationStore.setState({
    roomId: null,
    conversations: [],
    activeConversationId: null,
    isLoading: false,
    isHistoryOpen: false,
  });
}

describe('conversation_store', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    resetConversationStore();
  });

  it('loads conversation history without requiring an auth token', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        conversations: [
          {
            id: 21,
            room_id: 'room-guest',
            title: 'Canvas chat',
            mode: 'planning',
            is_active: true,
            message_count: 2,
            created_at: 1,
            updated_at: 2,
          },
        ],
      },
    });

    useConversationStore.getState().setRoomId('room-guest');

    await useConversationStore.getState().fetchConversations();

    expect(apiClient.get).toHaveBeenCalledWith('/ai/conversations/room-guest');
    expect(useConversationStore.getState().conversations).toHaveLength(1);
    expect(useConversationStore.getState().activeConversationId).toBe(21);
  });

  it('loads conversations through apiClient and keeps the active one selected', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        conversations: [
          {
            id: 11,
            room_id: 'room-1',
            title: 'Planning',
            mode: 'planning',
            is_active: false,
            message_count: 3,
            created_at: 1,
            updated_at: 2,
          },
          {
            id: 12,
            room_id: 'room-1',
            title: 'Agent',
            mode: 'agent',
            is_active: true,
            message_count: 5,
            created_at: 3,
            updated_at: 4,
          },
        ],
      },
    });

    useConversationStore.setState({ roomId: 'room-1' });
    await useConversationStore.getState().fetchConversations();

    expect(apiClient.get).toHaveBeenCalledWith('/ai/conversations/room-1');
    expect(useConversationStore.getState().conversations).toHaveLength(2);
    expect(useConversationStore.getState().activeConversationId).toBe(12);
  });

  it('switches to the newly created conversation before refreshing the list', async () => {
    (apiClient.post as Mock).mockResolvedValue({
      data: {
        conversation_id: 33,
      },
    });
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        conversations: [
          {
            id: 33,
            room_id: 'room-1',
            title: 'New conversation',
            mode: 'planning',
            is_active: true,
            message_count: 0,
            created_at: 10,
            updated_at: 10,
          },
        ],
      },
    });

    useConversationStore.setState({ roomId: 'room-1', activeConversationId: 12 });

    const conversationId = await useConversationStore.getState().createConversation();

    expect(apiClient.post).toHaveBeenCalledWith('/ai/conversations/room-1', {
      title: 'New conversation',
      mode: 'planning',
    });
    expect(apiClient.get).toHaveBeenCalledWith('/ai/conversations/room-1');
    expect(conversationId).toBe(33);
    expect(useConversationStore.getState().activeConversationId).toBe(33);
  });

  it('persists the selected conversation as active on the backend', async () => {
    (apiClient.patch as Mock).mockResolvedValue({
      data: {
        status: 'updated',
        is_active: true,
      },
    });

    useConversationStore.setState({
      roomId: 'room-1',
      activeConversationId: 12,
      conversations: [
        {
          id: 12,
          room_id: 'room-1',
          title: 'Planning',
          mode: 'planning',
          is_active: true,
          message_count: 3,
          created_at: 1,
          updated_at: 2,
        },
        {
          id: 13,
          room_id: 'room-1',
          title: 'Mermaid',
          mode: 'mermaid',
          is_active: false,
          message_count: 1,
          created_at: 3,
          updated_at: 4,
        },
      ],
    });

    await useConversationStore.getState().selectConversation(13);

    expect(apiClient.patch).toHaveBeenCalledWith('/ai/conversations/room-1/13', {
      is_active: true,
    });
    expect(useConversationStore.getState().activeConversationId).toBe(13);
    expect(useConversationStore.getState().conversations.map((conversation) => conversation.is_active))
      .toEqual([false, true]);
  });
});
