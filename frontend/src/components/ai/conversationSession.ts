export interface ConversationSessionSnapshot<Message> {
  messages: Message[];
  expandedMessageIds: string[];
  input: string;
}

const EMPTY_SNAPSHOT: ConversationSessionSnapshot<never> = {
  messages: [],
  expandedMessageIds: [],
  input: '',
};

export function getConversationSessionKey(conversationId?: number | null): string {
  return conversationId == null ? 'draft' : `conversation:${conversationId}`;
}

export function stashConversationSession<Message>(
  sessions: Map<string, ConversationSessionSnapshot<Message>>,
  key: string,
  snapshot: ConversationSessionSnapshot<Message>,
): void {
  sessions.set(key, {
    messages: [...snapshot.messages],
    expandedMessageIds: [...snapshot.expandedMessageIds],
    input: snapshot.input,
  });
}

export function restoreConversationSession<Message>(
  sessions: Map<string, ConversationSessionSnapshot<Message>>,
  key: string,
): ConversationSessionSnapshot<Message> {
  const snapshot = sessions.get(key);
  if (!snapshot) {
    return EMPTY_SNAPSHOT as ConversationSessionSnapshot<Message>;
  }

  return {
    messages: [...snapshot.messages],
    expandedMessageIds: [...snapshot.expandedMessageIds],
    input: snapshot.input,
  };
}
