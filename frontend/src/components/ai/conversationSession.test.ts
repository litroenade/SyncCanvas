import { describe, expect, it } from 'vitest';

import {
  getConversationSessionKey,
  restoreConversationSession,
  stashConversationSession,
  type ConversationSessionSnapshot,
} from './conversationSession';

interface FakeMessage {
  id: string;
}

describe('conversationSession', () => {
  it('uses stable keys for persisted conversations and the draft state', () => {
    expect(getConversationSessionKey(null)).toBe('draft');
    expect(getConversationSessionKey(undefined)).toBe('draft');
    expect(getConversationSessionKey(7)).toBe('conversation:7');
  });

  it('returns an empty snapshot when a conversation has no cached state', () => {
    const sessions = new Map<string, ConversationSessionSnapshot<FakeMessage>>();

    expect(restoreConversationSession(sessions, 'conversation:9')).toEqual({
      messages: [],
      expandedMessageIds: [],
      input: '',
    });
  });

  it('stores and restores snapshots without leaking mutable references', () => {
    const sessions = new Map<string, ConversationSessionSnapshot<FakeMessage>>();

    stashConversationSession(sessions, 'conversation:4', {
      messages: [{ id: 'assistant-1' }],
      expandedMessageIds: ['assistant-1'],
      input: 'transformer diagram',
    });

    const restored = restoreConversationSession(sessions, 'conversation:4');
    restored.messages.push({ id: 'assistant-2' });
    restored.expandedMessageIds.push('assistant-2');

    expect(restoreConversationSession(sessions, 'conversation:4')).toEqual({
      messages: [{ id: 'assistant-1' }],
      expandedMessageIds: ['assistant-1'],
      input: 'transformer diagram',
    });
  });
});
