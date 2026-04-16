import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AIStreamClient,
  getDefaultAIStreamConnectionError,
} from './ai';

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason, wasClean: true } as CloseEvent);
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  emitError() {
    this.onerror?.(new Event('error'));
  }
}

describe('AIStreamClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    localStorage.clear();
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('does not append the token query parameter to the websocket URL', async () => {
    localStorage.setItem('token', 'token with space');

    const client = new AIStreamClient('room-1');
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    expect(socket.url).toContain('/api/ai/stream/room-1?client_session_id=');
    expect(socket.url).not.toContain('token=');

    socket.open();
    await expect(connectPromise).resolves.toBeUndefined();
  });

  it('rejects pre-open close events with a mapped room access message', async () => {
    const client = new AIStreamClient('room-1');
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.close(1008, 'room_membership_required');

    await expect(connectPromise).rejects.toThrow('You do not have access to this room.');
  });

  it('treats close reasons with whitespace as mappable reasons', async () => {
    const client = new AIStreamClient('room-1');
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.close(1008, '  room_not_found ');

    await expect(connectPromise).rejects.toThrow('This room does not exist or has been deleted.');
  });

  it('invokes onClose after the websocket has already connected', async () => {
    const onClose = vi.fn();
    const client = new AIStreamClient('room-1', { onClose });
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.open();
    await connectPromise;
    socket.close(1000, '');

    expect(onClose).toHaveBeenCalledWith(
      expect.objectContaining({
        code: 1000,
        reason: '',
        wasClean: true,
      }),
    );
  });

  it('does not invoke onClose callback when closed before websocket is opened', async () => {
    const onClose = vi.fn();
    const client = new AIStreamClient('room-1', { onClose });
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.close(1008, 'authentication_required');

    await expect(connectPromise).rejects.toThrow(
      'Your login session has expired. Please sign in again.',
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it('falls back to the default message for unknown close reasons', async () => {
    const client = new AIStreamClient('room-1');
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.close(1008, 'unexpected_reason');

    await expect(connectPromise).rejects.toThrow(getDefaultAIStreamConnectionError());
  });

  it('falls back to default message when close reason is empty', async () => {
    const client = new AIStreamClient('room-1');
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.close(1008, '');

    await expect(connectPromise).rejects.toThrow(getDefaultAIStreamConnectionError());
  });

  it('reconnects automatically after a post-open transport close when autoReconnect is enabled', async () => {
    vi.useFakeTimers();

    const client = new AIStreamClient(
      'room-1',
      {},
      {
        autoReconnect: true,
        reconnectInitialDelayMs: 10,
        reconnectMaxDelayMs: 10,
      },
    );
    const connectPromise = client.connect();
    const socket = MockWebSocket.instances[0];

    socket.open();
    await connectPromise;

    socket.close(1012, '');

    await vi.advanceTimersByTimeAsync(10);

    expect(MockWebSocket.instances).toHaveLength(2);
  });
});
