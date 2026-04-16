import { useCallback, useEffect, useRef, useState } from 'react';

import { yjsManager, type BinaryFiles, type ExcalidrawElement } from '../lib/yjs';
import { useCollabEventStore } from '../stores/collab_event_store';
import type { CollabEvent, CollabEventType } from '../types';
import { SINGLETON_USER_LABEL } from '../config/singletonCanvas';

type AppState = Record<string, unknown>;

interface ChangeHandlingOptions {
  skipYjsSync?: boolean;
  skipManagedReverseSync?: boolean;
}

const LOCAL_ORIGINS = [
  'excalidraw-sync',
  'excalidraw-add',
  'excalidraw-update',
  'excalidraw-delete',
  'excalidraw-clear',
  'excalidraw-files-sync',
  'diagram-bundle-sync',
  'diagram-bundle-apply',
];

const MAX_EVENTS_PER_BATCH = 10;

const getRandomColor = (str?: string) => {
  const colors = [
    '#ef4444',
    '#f97316',
    '#f59e0b',
    '#84cc16',
    '#10b981',
    '#06b6d4',
    '#3b82f6',
    '#6366f1',
    '#8b5cf6',
    '#d946ef',
    '#f43f5e',
  ];
  if (!str) return colors[Math.floor(Math.random() * colors.length)];

  let hash = 0;
  for (let index = 0; index < str.length; index += 1) {
    hash = str.charCodeAt(index) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

const generateUserInfo = () => {
  const storedUsername = localStorage.getItem('username');
  const name = storedUsername || `${SINGLETON_USER_LABEL} ${Math.floor(Math.random() * 1000)}`;
  const color = getRandomColor(name);
  return { name, color };
};

let cachedUserInfo: { name: string; color: string } | null = null;

const getUserInfo = () => {
  if (!cachedUserInfo) {
    cachedUserInfo = generateUserInfo();
  }
  return cachedUserInfo;
};

const makeEventSummary = (element: ExcalidrawElement, fallbackType: string) => {
  const text = typeof (element as Record<string, unknown>).text === 'string'
    ? String((element as Record<string, unknown>).text)
    : '';
  const trimmed = text ? `${text.slice(0, 12)}${text.length > 12 ? '…' : ''}` : '';
  return trimmed ? `${fallbackType} · ${trimmed}` : fallbackType;
};

const buildEvents = (
  prevMap: Map<string, ExcalidrawElement>,
  nextElements: readonly ExcalidrawElement[],
  actorName: string,
  actorId: string,
  isMe: boolean,
): {
  events: CollabEvent[];
  nextMap: Map<string, ExcalidrawElement>;
  changedElementIds: string[];
  deletedElementIds: string[];
} => {
  const nextMap = new Map<string, ExcalidrawElement>();
  nextElements.forEach((element) => nextMap.set(element.id, element));

  const added: ExcalidrawElement[] = [];
  const deleted: ExcalidrawElement[] = [];
  const updated: ExcalidrawElement[] = [];

  nextMap.forEach((element, id) => {
    if (!prevMap.has(id)) {
      added.push(element);
      return;
    }

    const previous = prevMap.get(id);
    if (previous && JSON.stringify(previous) !== JSON.stringify(element)) {
      updated.push(element);
    }
  });

  prevMap.forEach((element, id) => {
    if (!nextMap.has(id)) {
      deleted.push(element);
    }
  });

  const events: CollabEvent[] = [];
  const ts = Date.now();
  const typeLabels: Record<CollabEventType, string> = {
    add: 'added',
    delete: 'deleted',
    update: 'updated',
  };

  const pushList = (items: ExcalidrawElement[], type: CollabEventType) => {
    items.slice(0, MAX_EVENTS_PER_BATCH).forEach((element) => {
      events.push({
        id: `${ts}-${type}-${element.id}`,
        ts,
        actorId,
        actorName,
        type,
        elementType: element.type,
        summary: makeEventSummary(element, element.type),
        isMe,
      });
    });

    if (items.length > MAX_EVENTS_PER_BATCH) {
      events.push({
        id: `${ts}-${type}-bulk`,
        ts,
        actorId,
        actorName,
        type,
        elementType: 'multiple',
        summary: `Batch ${typeLabels[type]} ${items.length} elements`,
        isMe,
      });
    }
  };

  pushList(added, 'add');
  pushList(deleted, 'delete');
  pushList(updated, 'update');

  return {
    events,
    nextMap,
    changedElementIds: [...added, ...updated].map((element) => element.id),
    deletedElementIds: deleted.map((element) => element.id),
  };
};

export interface Collaborator {
  pointer?: { x: number; y: number };
  button?: 'up' | 'down';
  selectedElementIds?: Record<string, boolean>;
  username?: string;
  color?: { background: string; stroke: string };
  id?: string;
}

export const useCanvas = (roomId?: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isSynced, setIsSynced] = useState(false);
  const [elements, setElements] = useState<readonly ExcalidrawElement[]>([]);
  const [files, setFiles] = useState<BinaryFiles>({});
  const [collaborators, setCollaborators] = useState<Map<string, Collaborator>>(new Map());

  const userInfoRef = useRef(getUserInfo());
  const lastSyncedElementsRef = useRef<string>('');
  const lastElementsMapRef = useRef<Map<string, ExcalidrawElement>>(new Map());
  const addEvents = useCollabEventStore((state) => state.addEvents);

  useEffect(() => {
    if (!roomId) {
      console.log('[useCanvas] No room id provided, skipping Yjs connection.');
      return;
    }

    lastSyncedElementsRef.current = '';
    lastElementsMapRef.current = new Map();
    yjsManager.connect(roomId);

    const provider = yjsManager.provider;
    const elementsArray = yjsManager.elementsArray;
    const filesMap = yjsManager.filesMap;

    if (!elementsArray) {
      console.error('[useCanvas] Failed to initialize Excalidraw Yjs bindings.');
      return;
    }

    setIsConnected(Boolean(provider));
    if (!provider) {
      setIsSynced(true);
    }

    const handleStatus = (event: { status: string }) => {
      console.log(`[useCanvas] provider status: ${event.status}`);
      setIsConnected(event.status === 'connected');
    };

    const handleSync = (synced: boolean) => {
      console.log(`[useCanvas] sync state: ${synced ? 'synced' : 'syncing'}`);
      setIsSynced(synced);
    };

    if (provider) {
      provider.on('status', handleStatus);
      provider.on('sync', handleSync);
    }

    const observer = (event: { transaction?: { origin?: unknown } }) => {
      const origin = event.transaction?.origin;
      if (typeof origin === 'string' && LOCAL_ORIGINS.includes(origin)) {
        return;
      }

      const newElements = yjsManager.getElements();
      const newElementsStr = JSON.stringify(newElements);
      const isInitial = origin === 'initial';

      const { events, nextMap } = buildEvents(
        lastElementsMapRef.current,
        newElements,
        'Remote user',
        'remote',
        false,
      );
      if (!isInitial && events.length > 0) {
        addEvents(events);
      }
      lastElementsMapRef.current = nextMap;

      if (newElementsStr !== lastSyncedElementsRef.current) {
        lastSyncedElementsRef.current = newElementsStr;
        setElements(newElements);
      }
    };

    const filesObserver = (event: { transaction?: { origin?: unknown } }) => {
      if (event.transaction?.origin === 'excalidraw-files-sync') {
        return;
      }
      setFiles(yjsManager.getFiles());
    };

    elementsArray.observe(observer);
    filesMap?.observe(filesObserver);

    observer({ transaction: { origin: 'initial' } });
    filesObserver({ transaction: { origin: 'initial' } });

    let awarenessObserver: (() => void) | null = null;
    if (provider) {
      const awareness = provider.awareness;
      const { name: myName, color: myColor } = userInfoRef.current;

      awareness.setLocalStateField('user', {
        name: myName,
        color: myColor,
      });

      awarenessObserver = () => {
        const states = awareness.getStates();
        const nextCollaborators = new Map<string, Collaborator>();

        states.forEach((state: Record<string, unknown>, clientId: number) => {
          if (clientId === awareness.clientID || !state.user) {
            return;
          }

          const user = state.user as { name?: string; color?: string };
          const pointer = state.pointer as { x: number; y: number } | undefined;
          nextCollaborators.set(String(clientId), {
            pointer,
            username: user.name,
            color: {
              background: user.color || '#000000',
              stroke: user.color || '#000000',
            },
            id: String(clientId),
          });
        });

        setCollaborators(nextCollaborators);
      };

      awareness.on('change', awarenessObserver);
    }

    return () => {
      elementsArray.unobserve(observer);
      filesMap?.unobserve(filesObserver);

      if (provider) {
        if (awarenessObserver) {
          provider.awareness.off('change', awarenessObserver);
        }
        provider.off('status', handleStatus);
        provider.off('sync', handleSync);
      }
    };
  }, [roomId, addEvents]);

  const handleChange = useCallback((
    newElements: readonly ExcalidrawElement[],
    _appState: AppState,
    newFiles: BinaryFiles,
    options: ChangeHandlingOptions = {},
  ) => {
    const previousElementsMap = lastElementsMapRef.current;
    const {
      events,
      nextMap,
      changedElementIds,
      deletedElementIds,
    } = buildEvents(
      previousElementsMap,
      newElements,
      userInfoRef.current.name,
      userInfoRef.current.name,
      true,
    );

    if (events.length > 0) {
      addEvents(events);
    }
    lastElementsMapRef.current = nextMap;

    const newElementsStr = JSON.stringify(newElements);
    if (newElementsStr !== lastSyncedElementsRef.current) {
      lastSyncedElementsRef.current = newElementsStr;

      if (!options.skipYjsSync) {
        yjsManager.syncElements(newElements);
      }

      if (!options.skipManagedReverseSync) {
        yjsManager.reverseSyncManagedElements(newElements, {
          previousElements: previousElementsMap,
          changedElementIds,
          deletedElementIds,
        });
      }
    }

    if (newFiles && Object.keys(newFiles).length > 0 && !options.skipYjsSync) {
      yjsManager.syncFiles(newFiles);
    }
  }, [addEvents]);

  const updatePointer = useCallback((pointer: { x: number; y: number }) => {
    const awareness = yjsManager.getAwareness();
    awareness?.setLocalStateField('pointer', pointer);
  }, []);

  const undo = useCallback(() => {
    yjsManager.undoManager?.undo();
  }, []);

  const redo = useCallback(() => {
    yjsManager.undoManager?.redo();
  }, []);

  const leaveRoom = useCallback(() => {
    yjsManager.disconnect();
    setElements([]);
    setFiles({});
    setCollaborators(new Map());
  }, []);

  return {
    elements,
    files,
    collaborators,
    isConnected,
    isSynced,
    handleChange,
    updatePointer,
    undo,
    redo,
    leaveRoom,
    currentRoomId: yjsManager.roomId,
  };
};
