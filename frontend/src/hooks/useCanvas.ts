/**
 * 模块名称：useCanvas
 * 主要功能：Excalidraw 与 Yjs 同步的 React Hook
 * 
 * 提供 Excalidraw 组件所需的状态管理和同步方法。
 */
import { useEffect, useCallback, useState, useRef } from 'react';
import { yjsManager, ExcalidrawElement, BinaryFiles } from '../lib/yjs';
import { useCollabEventStore } from '../stores/collab_event_store';
import type { CollabEvent, CollabEventType } from '../types';

// AppState 简化类型定义
type AppState = Record<string, unknown>;

/**
 * 生成随机颜色（基于字符串哈希）
 */
const getRandomColor = (str?: string) => {
    const colors = ['#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e'];
    if (!str) return colors[Math.floor(Math.random() * colors.length)];

    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
};

/**
 * 生成用户信息（缓存）
 */

/**
 * good
 */

const generateUserInfo = () => {
    const storedUsername = localStorage.getItem('username');
    const name = storedUsername || `Guest ${Math.floor(Math.random() * 1000)}`;
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

const MAX_EVENTS_PER_BATCH = 10;

const makeEventSummary = (element: ExcalidrawElement, fallbackType: string) => {
    const text = typeof (element as { text?: string }).text === 'string'
        ? (element as { text: string }).text
        : '';
    const trimmed = text ? `${text.slice(0, 12)}${text.length > 12 ? '…' : ''}` : '';
    return trimmed ? `${fallbackType}${trimmed ? ` · ${trimmed}` : ''}` : fallbackType;
};

const buildEvents = (
    prevMap: Map<string, ExcalidrawElement>,
    nextElements: readonly ExcalidrawElement[],
    actorName: string,
    actorId: string,
    isMe: boolean,
): { events: CollabEvent[]; nextMap: Map<string, ExcalidrawElement> } => {
    const nextMap = new Map<string, ExcalidrawElement>();
    nextElements.forEach(el => nextMap.set(el.id, el));

    const added: ExcalidrawElement[] = [];
    const deleted: ExcalidrawElement[] = [];
    const updated: ExcalidrawElement[] = [];

    nextMap.forEach((el, id) => {
        if (!prevMap.has(id)) {
            added.push(el);
            return;
        }
        const prev = prevMap.get(id)!;
        if (JSON.stringify(prev) !== JSON.stringify(el)) {
            updated.push(el);
        }
    });

    prevMap.forEach((el, id) => {
        if (!nextMap.has(id)) {
            deleted.push(el);
        }
    });

    const events: CollabEvent[] = [];
    const ts = Date.now();
    const typeLabels: Record<CollabEventType, string> = { add: '新增', delete: '删除', update: '更新' };

    const pushList = (items: ExcalidrawElement[], type: CollabEventType) => {
        items.slice(0, MAX_EVENTS_PER_BATCH).forEach((el) => {
            events.push({
                id: `${ts}-${type}-${el.id}`,
                ts,
                actorId,
                actorName,
                type,
                elementType: el.type,
                summary: makeEventSummary(el, el.type),
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
                summary: `批量${typeLabels[type]} ${items.length} 项`,
                isMe,
            });
        }
    };

    pushList(added, 'add');
    pushList(deleted, 'delete');
    pushList(updated, 'update');

    return { events, nextMap };
};

/**
 * Excalidraw 协作者光标接口
 */
export interface Collaborator {
    pointer?: { x: number; y: number };
    button?: 'up' | 'down';
    selectedElementIds?: Record<string, boolean>;
    username?: string;
    color?: { background: string; stroke: string };
    id?: string;
}

/**
 * Canvas Yjs 同步 Hook
 */
export const useCanvas = (roomId?: string) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isSynced, setIsSynced] = useState(false);
    const [elements, setElements] = useState<readonly ExcalidrawElement[]>([]);
    const [files, setFiles] = useState<BinaryFiles>({});
    const [collaborators, setCollaborators] = useState<Map<string, Collaborator>>(new Map());

    const userInfoRef = useRef(getUserInfo());
    const lastSyncedElementsRef = useRef<string>('');
    const lastElementsMapRef = useRef<Map<string, ExcalidrawElement>>(new Map());
    const addEvents = useCollabEventStore(state => state.addEvents);

    // 监听 Yjs 文档变化
    useEffect(() => {
        if (!roomId) {
            console.log('没有 roomId，跳过连接');
            return;
        }

        // 连接到房间
        yjsManager.connect(roomId);

        const provider = yjsManager.provider;
        const elementsArray = yjsManager.elementsArray;
        const filesMap = yjsManager.filesMap;

        if (!elementsArray) {
            console.error('Excalidraw Yjs 初始化失败');
            return;
        }

        setIsConnected(!!provider);
        if (!provider) {
            setIsSynced(true);
        }

        // 监听连接状态
        const handleStatus = (event: { status: string }) => {
            console.log(`Excalidraw Yjs 连接状态: ${event.status}`);
            setIsConnected(event.status === 'connected');
        };

        const handleSync = (synced: boolean) => {
            console.log(`Excalidraw Yjs 同步状态: ${synced ? '已同步' : '同步中'}`);
            setIsSynced(synced);
        };

        if (provider) {
            provider.on('status', handleStatus);
            provider.on('sync', handleSync);
        }

        // 监听元素变化
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const observer = (event: any) => {
            const origin = event.transaction?.origin;
            const addedCount = event.changes?.added?.size || 0;
            const deletedCount = event.changes?.deleted?.size || 0;

            // ========== 诊断日志 ==========
            console.log('[useCanvas] ========== Y.Array observe 触发 ==========');
            console.log('[useCanvas] origin:', origin, '| type:', typeof origin);
            console.log('[useCanvas] changes: added=' + addedCount + ', deleted=' + deletedCount);
            // ========== 诊断日志结束 ==========

            // 如果是本地发出的变更，忽略，避免触发 React 更新和 excalidraw updateScene
            // 注意: 只过滤明确的本地 origin
            const LOCAL_ORIGINS = ['excalidraw-sync', 'excalidraw-add', 'excalidraw-update', 'excalidraw-delete', 'excalidraw-clear', 'excalidraw-files-sync'];
            if (typeof origin === 'string' && LOCAL_ORIGINS.includes(origin)) {
                console.log('[useCanvas] 跳过本地变更:', origin);
                return;
            }

            const newElements = yjsManager.getElements();
            const newElementsStr = JSON.stringify(newElements);

            const isInitial = origin === 'initial';
            const { events, nextMap } = buildEvents(
                lastElementsMapRef.current,
                newElements,
                '远端用户',
                'remote',
                false,
            );
            if (!isInitial && events.length) {
                addEvents(events);
            }
            lastElementsMapRef.current = nextMap;

            console.log('[useCanvas] 获取元素数量:', newElements.length);
            // 打印前 2 个元素的 id 和 type
            if (newElements.length > 0) {
                console.log('[useCanvas] 元素样例:', newElements.slice(0, 2).map(el => ({ id: el.id, type: el.type })));
            }

            // 避免不必要的更新
            if (newElementsStr !== lastSyncedElementsRef.current) {
                lastSyncedElementsRef.current = newElementsStr;
                setElements(newElements);
                console.log('[useCanvas]   已更新 React state, 元素数量:', newElements.length);
            } else {
                console.log('[useCanvas] 元素无变化，跳过更新');
            }
        };

        // 监听文件变化
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const filesObserver = (event: any) => {
            // 同样过滤本地文件变更
            if (event.transaction.origin === 'excalidraw-files-sync') {
                return;
            }
            if (!filesMap) return;
            const newFiles = yjsManager.getFiles();
            setFiles(newFiles);
        };

        elementsArray.observe(observer);
        if (filesMap) {
            filesMap.observe(filesObserver);
        }
        // observer(); // 初始同步不需要调用，因为初始状态应该是空的或已有的
        // 但我们需要获取初始数据
        // 手动调用一次以加载初始数据，模拟非本地 origin
        observer({ transaction: { origin: 'initial' } });
        filesObserver({ transaction: { origin: 'initial' } });

        // Awareness（协作者光标）
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
                const newCollaborators = new Map<string, Collaborator>();

                states.forEach((state: Record<string, unknown>, clientId: number) => {
                    if (clientId !== awareness.clientID && state.user) {
                        const user = state.user as { name?: string; color?: string };
                        const pointer = state.pointer as { x: number; y: number } | undefined;

                        newCollaborators.set(String(clientId), {
                            pointer,
                            username: user.name,
                            color: {
                                background: user.color || '#000',
                                stroke: user.color || '#000',
                            },
                            id: String(clientId),
                        });
                    }
                });

                setCollaborators(newCollaborators);
            };

            awareness.on('change', awarenessObserver);
        }

        return () => {
            elementsArray.unobserve(observer);
            if (filesMap) {
                filesMap.unobserve(filesObserver);
            }
            if (provider) {
                if (awarenessObserver) {
                    provider.awareness.off('change', awarenessObserver);
                }
                provider.off('status', handleStatus);
                provider.off('sync', handleSync);
            }
        };
    }, [roomId, addEvents]);

    /**
     * 处理 Excalidraw onChange 事件
     * 将本地变更同步到 Yjs
     */
    const handleChange = useCallback((
        newElements: readonly ExcalidrawElement[],
        _appState: AppState,
        newFiles: BinaryFiles
    ) => {
        const { events, nextMap } = buildEvents(
            lastElementsMapRef.current,
            newElements,
            userInfoRef.current.name,
            userInfoRef.current.name,
            true,
        );
        if (events.length) {
            addEvents(events);
        }
        lastElementsMapRef.current = nextMap;

        const newElementsStr = JSON.stringify(newElements);

        // 避免循环更新
        if (newElementsStr === lastSyncedElementsRef.current) {
            // 即使元素没变，文件也可能变了，所以这里不能直接 return，或者需要分开判断
            // 但 Excalidraw 的机制通常是 files 变了 elements 也会变（引用了 fileId）
        }

        if (newElementsStr !== lastSyncedElementsRef.current) {
            lastSyncedElementsRef.current = newElementsStr;
            yjsManager.syncElements(newElements);
        }

        // 同步文件
        if (newFiles && Object.keys(newFiles).length > 0) {
            yjsManager.syncFiles(newFiles);
        }
    }, [addEvents]);

    /**
     * 更新协作者光标位置
     */
    const updatePointer = useCallback((pointer: { x: number; y: number }) => {
        const awareness = yjsManager.getAwareness();
        if (awareness) {
            awareness.setLocalStateField('pointer', pointer);
        }
    }, []);

    /**
     * 撤销
     */
    const undo = useCallback(() => {
        const undoManager = yjsManager.undoManager;
        if (undoManager) {
            undoManager.undo();
        }
    }, []);

    /**
     * 重做
     */
    const redo = useCallback(() => {
        const undoManager = yjsManager.undoManager;
        if (undoManager) {
            undoManager.redo();
        }
    }, []);

    /**
     * 离开房间
     */
    const leaveRoom = useCallback(() => {
        yjsManager.disconnect();
        setElements([]);
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
