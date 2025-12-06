import { useEffect, useCallback, useState, useRef } from 'react';
import { useCanvasStore, Shape } from '../stores/useCanvasStore';
import { yjsManager } from '../lib/yjs';

const getRandomColor = (str?: string) => {
    const colors = ['#ef4444', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e'];
    if (!str) return colors[Math.floor(Math.random() * colors.length)];

    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
};

// 生成稳定的用户信息（只在模块加载时生成一次）
const generateUserInfo = () => {
    const storedUsername = localStorage.getItem('username');
    const name = storedUsername || `Guest ${Math.floor(Math.random() * 1000)}`;
    const color = getRandomColor(name);
    return { name, color };
};

// 缓存用户信息
let cachedUserInfo: { name: string; color: string } | null = null;
const getUserInfo = () => {
    if (!cachedUserInfo) {
        cachedUserInfo = generateUserInfo();
    }
    return cachedUserInfo;
};

export const useYjs = (roomId?: string) => {
    const { setShapes, setCursors } = useCanvasStore();
    const [isConnected, setIsConnected] = useState(false);
    const [isSynced, setIsSynced] = useState(false);

    // 使用 ref 存储用户信息，避免触发重新渲染
    const userInfoRef = useRef(getUserInfo());
    const [, forceUpdate] = useState(0);

    // 监听文档变更 (用于预览)
    useEffect(() => {
        const handleDocChange = () => {
            forceUpdate(v => v + 1);
        };
        yjsManager.onDocChange(handleDocChange);
        return () => {
            yjsManager.offDocChange(handleDocChange);
        };
    }, []);

    useEffect(() => {
        // 如果没有 roomId，不连接
        if (!roomId) {
            console.log('没有 roomId，跳过连接');
            return;
        }

        // 连接到房间
        yjsManager.connect(roomId);

        const shapesMap = yjsManager.shapesMap;
        const provider = yjsManager.provider;

        // 如果没有 shapesMap，说明初始化失败
        if (!shapesMap) {
            console.error('Yjs 初始化失败');
            return;
        }

        // 设置连接状态
        setIsConnected(!!provider);
        if (!provider) {
            // 预览模式：视为已同步
            setIsSynced(true);
        }

        // 监听连接状态 (仅当有 provider 时)
        const handleStatus = (event: { status: string }) => {
            console.log(`Yjs 连接状态: ${event.status}`);
        };

        const handleSync = (synced: boolean) => {
            console.log(`Yjs 同步状态: ${synced ? '已同步' : '同步中'}`);
            setIsSynced(synced);
        };

        if (provider) {
            provider.on('status', handleStatus);
            provider.on('sync', handleSync);
        }

        // 从 Yjs 同步到 Store
        const observer = () => {
            const shapes = shapesMap.toJSON() as Record<string, Shape>;
            setShapes(shapes);
        };

        shapesMap.observe(observer);

        // 初始同步
        observer();

        // Awareness (仅当有 provider 时)
        let awarenessObserver: (() => void) | null = null;

        if (provider) {
            const awareness = provider.awareness;

            // 获取用户信息
            const { name: myName, color: myColor } = userInfoRef.current;

            // 设置本地状态
            awareness.setLocalStateField('user', {
                name: myName,
                color: myColor,
            });

            awarenessObserver = () => {
                const states = awareness.getStates();
                const cursors: Record<string, any> = {};

                states.forEach((state: any, clientId: number) => {
                    if (clientId !== awareness.clientID && state.user && state.cursor) {
                        cursors[clientId] = {
                            ...state.cursor,
                            ...state.user,
                        };
                    }
                });

                setCursors(cursors);
            };

            awareness.on('change', awarenessObserver);
        }

        return () => {
            shapesMap.unobserve(observer);
            if (provider) {
                if (awarenessObserver) {
                    provider.awareness.off('change', awarenessObserver);
                }
                provider.off('status', handleStatus);
                provider.off('sync', handleSync);
            }
            // 注意：不在这里断开连接，因为可能是组件重新渲染
            // 断开连接应该在用户主动离开房间时进行
        };
    }, [roomId, setShapes, setCursors]);

    // 更新 Yjs 的操作
    const addShapeToYjs = useCallback((shape: Shape) => {
        const shapesMap = yjsManager.shapesMap;
        if (!shapesMap) {
            console.warn('Yjs 未连接，无法添加图形');
            return;
        }
        shapesMap.set(shape.id, shape);
    }, []);

    const updateShapeInYjs = useCallback((id: string, attrs: Partial<Shape>) => {
        const shapesMap = yjsManager.shapesMap;
        if (!shapesMap) {
            console.warn('Yjs 未连接，无法更新图形');
            return;
        }
        const currentShape = shapesMap.get(id) as Shape | undefined;
        if (currentShape) {
            const updatedShape = { ...currentShape, ...attrs };
            shapesMap.set(id, updatedShape);
        }
    }, []);

    const deleteShapeInYjs = useCallback((id: string) => {
        const shapesMap = yjsManager.shapesMap;
        if (!shapesMap) {
            console.warn('Yjs 未连接，无法删除图形');
            return;
        }
        shapesMap.delete(id);
    }, []);

    const undo = useCallback(() => {
        const undoManager = yjsManager.undoManager;
        if (!undoManager) {
            console.warn('Yjs 未连接，无法撤销');
            return;
        }
        undoManager.undo();
    }, []);

    const redo = useCallback(() => {
        const undoManager = yjsManager.undoManager;
        if (!undoManager) {
            console.warn('Yjs 未连接，无法重做');
            return;
        }
        undoManager.redo();
    }, []);

    const updateAwareness = useCallback((x: number, y: number) => {
        const awareness = yjsManager.getAwareness();
        if (awareness) {
            awareness.setLocalStateField('cursor', { x, y });
        }
    }, []);

    const updateShapesInYjs = useCallback((updates: Record<string, Partial<Shape>>) => {
        const ydoc = yjsManager.ydoc;
        const shapesMap = yjsManager.shapesMap;
        if (!ydoc || !shapesMap) return;

        ydoc.transact(() => {
            Object.entries(updates).forEach(([id, attrs]) => {
                const currentShape = shapesMap.get(id) as Shape | undefined;
                if (currentShape) {
                    const updatedShape = { ...currentShape, ...attrs };
                    shapesMap.set(id, updatedShape);
                }
            });
        });
    }, []);

    const leaveRoom = useCallback(() => {
        yjsManager.disconnect();
        setShapes({});
        setCursors({});
    }, [setShapes, setCursors]);

    return {
        addShape: addShapeToYjs,
        updateShape: updateShapeInYjs,
        updateShapes: updateShapesInYjs,
        deleteShape: deleteShapeInYjs,
        undo,
        redo,
        updateAwareness,
        leaveRoom,
        isConnected,
        isSynced,
        currentRoomId: yjsManager.roomId,
    };
};
