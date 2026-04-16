import { useCallback, useEffect, useRef, useState } from 'react';

import {
  AIStreamClient,
  getDefaultAIStreamConnectionError,
  mapAIStreamCloseReason,
  type AIStreamComplete,
  type AIStreamError,
  type AIStreamCloseInfo,
  type DiagramGenerationMode,
  type AIStreamRequestOptions,
  type AIStreamStarted,
  type AIStreamStep,
} from '../services/api/ai';
import type { DiagramBundle } from '../types';

export interface UseAIStreamOptions {
  roomId: string;
  autoConnect?: boolean;
  roomVersion?: number;
}

export interface AIStreamState {
  isConnected: boolean;
  isLoading: boolean;
  steps: AIStreamStep[];
  response: string | null;
  error: string | null;
  transportError: string | null;
  requestId: string | null;
  lastCloseInfo: AIStreamCloseInfo | null;
  closeInterruptedRequest: boolean;
  roomVersion: number | null;
  snapshotRequired: boolean;
  elementsCreated: string[];
  virtualElements: Record<string, unknown>[];
  diagramBundle: DiagramBundle | null;
  diagramFamily: string | null;
  generationMode: DiagramGenerationMode | null;
  managedScope: string[];
  patchSummary: string | null;
  unmanagedWarnings: string[];
  sources: Array<{
    type: string;
    provider?: string;
    model?: string;
    role?: string;
  }>;
  changeReasoning: Array<{ step: string; explanation: string }>;
  affectedNodeIds: string[];
  riskNotes: string[];
}

export interface UseAIStreamReturn extends AIStreamState {
  connect: () => Promise<void>;
  disconnect: () => void;
  sendRequest: (prompt: string, options?: AIStreamRequestOptions) => Promise<void>;
  reset: () => void;
}

function createClientSessionId(): string {
  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useAIStream({
  roomId,
  autoConnect = false,
  roomVersion,
}: UseAIStreamOptions): UseAIStreamReturn {
  const clientRef = useRef<AIStreamClient | null>(null);
  const connectPromiseRef = useRef<Promise<void> | null>(null);
  const roomVersionRef = useRef<number | null>(roomVersion ?? null);
  const clientSessionIdRef = useRef<string>(createClientSessionId());
  const latestRequestIdRef = useRef<string | null>(null);

  const [state, setState] = useState<AIStreamState>({
    isConnected: false,
    isLoading: false,
    steps: [],
    response: null,
    error: null,
    transportError: null,
    requestId: null,
    lastCloseInfo: null,
    closeInterruptedRequest: false,
    roomVersion: null,
    snapshotRequired: false,
    elementsCreated: [],
    virtualElements: [],
    diagramBundle: null,
    diagramFamily: null,
    generationMode: null,
    managedScope: [],
    patchSummary: null,
    unmanagedWarnings: [],
    sources: [],
    changeReasoning: [],
    affectedNodeIds: [],
    riskNotes: [],
  });

  useEffect(() => {
    roomVersionRef.current = roomVersion ?? null;
    clientSessionIdRef.current = createClientSessionId();
    latestRequestIdRef.current = null;
  }, [roomId, roomVersion]);

  const matchesActiveRequest = useCallback((requestId?: string | null) => {
    const activeRequestId = latestRequestIdRef.current;
    if (!activeRequestId) {
      return true;
    }
    return requestId === activeRequestId;
  }, []);

  const handleStep = useCallback((step: AIStreamStep) => {
    if (!matchesActiveRequest(step.request_id)) {
      return;
    }
    if (step.request_id) {
      latestRequestIdRef.current = step.request_id;
    }
    setState((prev) => ({
      ...prev,
      requestId: step.request_id ?? prev.requestId,
      steps: [...prev.steps, step],
    }));
  }, [matchesActiveRequest]);

  const handleComplete = useCallback((result: AIStreamComplete) => {
    if (!matchesActiveRequest(result.request_id)) {
      return;
    }
    if (result.request_id) {
      latestRequestIdRef.current = result.request_id;
    }
    if (typeof result.room_version === 'number') {
      roomVersionRef.current = result.room_version;
    }
    if (result.status !== 'success') {
      const errorMessage = result.message || result.response || 'AI request failed';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        response: null,
        error: errorMessage,
        transportError: null,
        requestId: result.request_id ?? prev.requestId,
        closeInterruptedRequest: false,
        roomVersion: typeof result.room_version === 'number' ? result.room_version : prev.roomVersion,
      }));
      return;
    }
    setState((prev) => ({
      ...prev,
      isLoading: false,
      response: result.response,
      error: null,
      transportError: null,
      requestId: result.request_id ?? prev.requestId,
      elementsCreated: result.elements_created,
      virtualElements: result.virtual_elements || [],
      diagramBundle: result.diagram_bundle || null,
      diagramFamily: result.diagram_family || null,
      generationMode: result.generation_mode || null,
      managedScope: result.managed_scope || [],
      patchSummary: result.patch_summary || null,
      unmanagedWarnings: result.unmanaged_warnings || [],
      sources: result.sources || [],
      changeReasoning: result.change_reasoning || [],
      affectedNodeIds: result.affected_node_ids || [],
      riskNotes: result.risk_notes || [],
      closeInterruptedRequest: false,
      roomVersion: typeof result.room_version === 'number' ? result.room_version : prev.roomVersion,
    }));
  }, [matchesActiveRequest]);

  const handleError = useCallback((streamError: AIStreamError) => {
    if (!matchesActiveRequest(streamError.request_id)) {
      return;
    }
    if (streamError.request_id) {
      latestRequestIdRef.current = streamError.request_id;
    }
    setState((prev) => ({
      ...prev,
      isLoading: false,
      error: streamError.message,
      requestId: streamError.request_id ?? prev.requestId,
      closeInterruptedRequest: false,
    }));
  }, [matchesActiveRequest]);

  const handleStarted = useCallback((_started: AIStreamStarted) => {
    if (!matchesActiveRequest(_started.request_id)) {
      return;
    }
    if (_started.request_id) {
      latestRequestIdRef.current = _started.request_id;
    }
    if (typeof _started.room_version === 'number') {
      roomVersionRef.current = _started.room_version;
    }
    setState((prev) => ({
      ...prev,
      roomVersion: typeof _started.room_version === 'number' ? _started.room_version : prev.roomVersion,
      isLoading: true,
      steps: [],
      response: null,
      error: null,
      transportError: null,
      requestId: _started.request_id ?? prev.requestId,
      lastCloseInfo: null,
      closeInterruptedRequest: false,
      elementsCreated: [],
      virtualElements: [],
      diagramBundle: null,
      diagramFamily: null,
      generationMode: null,
      managedScope: [],
      patchSummary: null,
      unmanagedWarnings: [],
      sources: [],
      changeReasoning: [],
      affectedNodeIds: [],
      riskNotes: [],
    }));
  }, [matchesActiveRequest]);

  const handleClose = useCallback((_close: AIStreamCloseInfo) => {
    const defaultTransportError = getDefaultAIStreamConnectionError();
    if (_close.room_version != null) {
      roomVersionRef.current = _close.room_version;
    }
    const closeMessage = _close.reason
      ? mapAIStreamCloseReason(_close.reason)
      : _close.code === 1000 || (_close.code === 1005 && _close.wasClean)
        ? null
        : defaultTransportError;

    setState((prev) => ({
      ...prev,
      isConnected: false,
      isLoading: false,
      error:
        prev.isLoading
          ? closeMessage ?? defaultTransportError
          : prev.error,
      transportError: closeMessage,
      requestId: latestRequestIdRef.current,
      lastCloseInfo: _close,
      closeInterruptedRequest: prev.isLoading,
      snapshotRequired: _close.snapshot_required || false,
      roomVersion: _close.room_version != null ? _close.room_version : prev.roomVersion,
    }));
  }, []);

  const connect = useCallback(async () => {
    if (clientRef.current?.isConnected) {
      return;
    }
    if (connectPromiseRef.current) {
      await connectPromiseRef.current;
      return;
    }

    const client = new AIStreamClient(
      roomId,
      {
        onStep: handleStep,
        onComplete: handleComplete,
        onError: handleError,
        onStarted: handleStarted,
        onClose: handleClose,
      },
      {
        roomVersion: roomVersionRef.current ?? undefined,
        clientSessionId: clientSessionIdRef.current,
        autoReconnect: autoConnect,
      },
    );
    clientRef.current = client;

    const connectPromise = (async () => {
      try {
        await client.connect();
        setState((prev) => ({
          ...prev,
          isConnected: true,
          transportError: null,
          lastCloseInfo: null,
          closeInterruptedRequest: false,
        }));
      } catch (error) {
        const message =
          error instanceof Error && error.message
            ? error.message
            : getDefaultAIStreamConnectionError();
        console.error('[useAIStream] Failed to connect:', error);
        setState((prev) => ({
          ...prev,
          transportError: message,
          isConnected: false,
        }));
      } finally {
        if (clientRef.current === client && !client.isConnected) {
          clientRef.current = null;
        }
        connectPromiseRef.current = null;
      }
    })();
    connectPromiseRef.current = connectPromise;
    await connectPromise;
  }, [roomId, autoConnect, handleStep, handleComplete, handleError, handleStarted, handleClose]);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    clientRef.current = null;
    connectPromiseRef.current = null;
    roomVersionRef.current = null;
    latestRequestIdRef.current = null;
    setState((prev) => ({
      ...prev,
      isConnected: false,
      transportError: null,
      requestId: null,
      roomVersion: null,
      snapshotRequired: false,
      lastCloseInfo: null,
      closeInterruptedRequest: false,
    }));
  }, []);

  const sendRequest = useCallback(async (
    prompt: string,
    options?: AIStreamRequestOptions,
  ) => {
    if (!clientRef.current?.isConnected) {
      await connect();
    }

    if (!clientRef.current?.isConnected) {
      const defaultTransportError = getDefaultAIStreamConnectionError();
      setState((prev) => ({
        ...prev,
        error: prev.error || defaultTransportError,
        transportError: prev.transportError || defaultTransportError,
        closeInterruptedRequest: true,
      }));
      return;
    }

    const mode = options?.mode || 'agent';
    const adjustedOptions: AIStreamRequestOptions = {
      ...options,
      mode,
    };

    if (mode === 'planning') {
      adjustedOptions.virtual_mode = true;
    }

    latestRequestIdRef.current = adjustedOptions.request_id ?? null;
    setState((prev) => ({
      ...prev,
      error: null,
      transportError: null,
      requestId: adjustedOptions.request_id ?? prev.requestId,
      closeInterruptedRequest: false,
    }));

    clientRef.current.sendRequest(prompt, adjustedOptions);
  }, [connect]);

  const reset = useCallback(() => {
    latestRequestIdRef.current = null;
    setState({
      isConnected: clientRef.current?.isConnected ?? false,
      isLoading: false,
      steps: [],
      response: null,
      error: null,
      transportError: null,
      requestId: null,
      lastCloseInfo: null,
      closeInterruptedRequest: false,
      roomVersion: roomVersionRef.current,
      snapshotRequired: false,
      elementsCreated: [],
      virtualElements: [],
      diagramBundle: null,
      diagramFamily: null,
      generationMode: null,
      managedScope: [],
      patchSummary: null,
      unmanagedWarnings: [],
      sources: [],
      changeReasoning: [],
      affectedNodeIds: [],
      riskNotes: [],
    });
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, roomId, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    sendRequest,
    reset,
  };
}
