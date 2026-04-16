import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getDefaultAIStreamConnectionError } from '../services/api/ai';
import { useAIStream, type UseAIStreamReturn } from './useAIStream';

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

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(_data: string) {}

  close(code = 1000, reason = '', wasClean = true) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason, wasClean } as CloseEvent);
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  emitMessage(data: unknown) {
    this.onmessage?.({
      data: JSON.stringify(data),
    } as MessageEvent);
  }
}

interface HookHarnessProps {
  roomId?: string;
  autoConnect?: boolean;
  roomVersion?: number;
  onSnapshot: (stream: UseAIStreamReturn) => void;
}

function HookHarness({
  roomId = 'room-1',
  autoConnect = true,
  roomVersion,
  onSnapshot,
}: HookHarnessProps) {
  const stream = useAIStream({ roomId, autoConnect, roomVersion });

  useEffect(() => {
    onSnapshot(stream);
  }, [onSnapshot, stream]);

  return null;
}

function getClientSessionId(socket: MockWebSocket): string {
  return new URL(socket.url).searchParams.get('client_session_id') ?? '';
}

describe('useAIStream', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    MockWebSocket.instances = [];
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('keeps a single websocket after started updates the room version', async () => {
    let snapshot: UseAIStreamReturn | null = null;
    const latestSnapshot = (): UseAIStreamReturn => {
      expect(snapshot).not.toBeNull();
      return snapshot as UseAIStreamReturn;
    };

    await act(async () => {
      root.render(<HookHarness onSnapshot={(value) => { snapshot = value; }} />);
    });

    expect(MockWebSocket.instances).toHaveLength(1);

    await act(async () => {
      MockWebSocket.instances[0].open();
    });

    await act(async () => {
      MockWebSocket.instances[0].emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 7,
        prompt: 'Create a transformer-style architecture diagram.',
      });
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(latestSnapshot().roomVersion).toBe(7);
    expect(latestSnapshot().isLoading).toBe(true);
    expect(latestSnapshot().error).toBeNull();
    expect(latestSnapshot().transportError).toBeNull();
  });

  it('ignores websocket events for other client sessions and other request ids', async () => {
    let snapshot: UseAIStreamReturn | null = null;
    const latestSnapshot = (): UseAIStreamReturn => {
      expect(snapshot).not.toBeNull();
      return snapshot as UseAIStreamReturn;
    };

    await act(async () => {
      root.render(<HookHarness onSnapshot={(value) => { snapshot = value; }} />);
    });

    const socket = MockWebSocket.instances[0];
    const clientSessionId = getClientSessionId(socket);

    await act(async () => {
      socket.open();
    });

    await act(async () => {
      await latestSnapshot().sendRequest('Create diagram', {
        mode: 'agent',
        request_id: 'req-1',
      });
    });

    await act(async () => {
      socket.emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 7,
        prompt: 'foreign session',
        request_id: 'req-1',
        client_session_id: 'client-foreign',
      });
    });

    expect(latestSnapshot().isLoading).toBe(false);

    await act(async () => {
      socket.emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 7,
        prompt: 'foreign request',
        request_id: 'req-2',
        client_session_id: clientSessionId,
      });
    });

    expect(latestSnapshot().isLoading).toBe(false);

    await act(async () => {
      socket.emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 7,
        prompt: 'current request',
        request_id: 'req-1',
        client_session_id: clientSessionId,
      });
    });

    expect(latestSnapshot().isLoading).toBe(true);
    expect(latestSnapshot().requestId).toBe('req-1');
  });

  it('keeps transport close state separate after a completed request', async () => {
    let snapshot: UseAIStreamReturn | null = null;
    const latestSnapshot = (): UseAIStreamReturn => {
      expect(snapshot).not.toBeNull();
      return snapshot as UseAIStreamReturn;
    };

    await act(async () => {
      root.render(<HookHarness onSnapshot={(value) => { snapshot = value; }} />);
    });

    const socket = MockWebSocket.instances[0];
    const clientSessionId = getClientSessionId(socket);

    await act(async () => {
      socket.open();
    });

    await act(async () => {
      await latestSnapshot().sendRequest('Create diagram', {
        mode: 'agent',
        request_id: 'req-1',
      });
    });

    await act(async () => {
      socket.emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 3,
        prompt: 'Create diagram',
        request_id: 'req-1',
        client_session_id: clientSessionId,
      });
    });

    await act(async () => {
      socket.emitMessage({
        type: 'complete',
        status: 'success',
        response: 'Created diagram',
        run_id: 1,
        elements_created: [],
        tools_used: [],
        generation_mode: 'deterministic_seed',
        request_id: 'req-1',
        client_session_id: clientSessionId,
      });
    });

    await act(async () => {
      socket.close(1012, '', false);
    });

    expect(latestSnapshot().response).toBe('Created diagram');
    expect(latestSnapshot().generationMode).toBe('deterministic_seed');
    expect(latestSnapshot().error).toBeNull();
    expect(latestSnapshot().transportError).toBe(getDefaultAIStreamConnectionError());
    expect(latestSnapshot().closeInterruptedRequest).toBe(false);
  });

  it('treats complete messages with error status as request failures', async () => {
    let snapshot: UseAIStreamReturn | null = null;
    const latestSnapshot = (): UseAIStreamReturn => {
      expect(snapshot).not.toBeNull();
      return snapshot as UseAIStreamReturn;
    };

    await act(async () => {
      root.render(<HookHarness onSnapshot={(value) => { snapshot = value; }} />);
    });

    const socket = MockWebSocket.instances[0];
    const clientSessionId = getClientSessionId(socket);

    await act(async () => {
      socket.open();
    });

    await act(async () => {
      await latestSnapshot().sendRequest('Create blueprint', {
        mode: 'planning',
        request_id: 'req-error',
      });
    });

    await act(async () => {
      socket.emitMessage({
        type: 'started',
        room_id: 'room-1',
        room_version: 5,
        prompt: 'Create blueprint',
        request_id: 'req-error',
        client_session_id: clientSessionId,
      });
    });

    await act(async () => {
      socket.emitMessage({
        type: 'complete',
        status: 'error',
        code: 'TXN_ROLLBACK',
        message: "'plc'",
        response: '',
        run_id: 1,
        elements_created: [],
        tools_used: [],
        request_id: 'req-error',
        client_session_id: clientSessionId,
      });
    });

    expect(latestSnapshot().isLoading).toBe(false);
    expect(latestSnapshot().error).toBe("'plc'");
    expect(latestSnapshot().response).toBeNull();
  });

  it('does not surface a transport error for clean 1005 closes when idle', async () => {
    let snapshot: UseAIStreamReturn | null = null;
    const latestSnapshot = (): UseAIStreamReturn => {
      expect(snapshot).not.toBeNull();
      return snapshot as UseAIStreamReturn;
    };

    await act(async () => {
      root.render(<HookHarness onSnapshot={(value) => { snapshot = value; }} />);
    });

    const socket = MockWebSocket.instances[0];

    await act(async () => {
      socket.open();
    });

    await act(async () => {
      socket.close(1005, '', true);
    });

    expect(latestSnapshot().isConnected).toBe(false);
    expect(latestSnapshot().error).toBeNull();
    expect(latestSnapshot().transportError).toBeNull();
    expect(latestSnapshot().lastCloseInfo).toEqual(
      expect.objectContaining({
        code: 1005,
        reason: '',
        wasClean: true,
      }),
    );
  });
});
