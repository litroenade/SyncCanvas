import { useEffect, useCallback } from 'react';
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

const storedUsername = localStorage.getItem('username');
const myName = storedUsername || `Guest ${Math.floor(Math.random() * 1000)}`;
const myColor = getRandomColor(myName);

export const useYjs = (roomId?: string) => {
    const { setShapes, setCursors } = useCanvasStore();

    useEffect(() => {
        // 如果没有 roomId，使用默认房间
        const targetRoomId = roomId || 'default-room';
        
        // 连接到房间
        yjsManager.connect(targetRoomId);

        const shapesMap = yjsManager.shapesMap;
        const provider = yjsManager.provider;

        // 从 Yjs 同步到 Store
        const observer = () => {
            const shapes = shapesMap.toJSON() as Record<string, Shape>;
            setShapes(shapes);
        };

        shapesMap.observe(observer);
        
        // 初始同步
        observer();

        // Awareness
        const awareness = provider.awareness;

        // 设置本地状态
        awareness.setLocalStateField('user', {
            name: myName,
            color: myColor,
        });

        const awarenessObserver = () => {
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

        return () => {
            shapesMap.unobserve(observer);
            awareness.off('change', awarenessObserver);
            // 注意：不在这里断开连接，因为可能是组件重新渲染
            // 断开连接应该在用户主动离开房间时进行
        };
    }, [roomId, setShapes, setCursors]);

    // 更新 Yjs 的操作
    const addShapeToYjs = useCallback((shape: Shape) => {
        if (!yjsManager.isConnected) return;
        yjsManager.shapesMap.set(shape.id, shape);
    }, []);

    const updateShapeInYjs = useCallback((id: string, attrs: Partial<Shape>) => {
        if (!yjsManager.isConnected) return;
        const shapesMap = yjsManager.shapesMap;
        const currentShape = shapesMap.get(id) as Shape | undefined;
        if (currentShape) {
            const updatedShape = { ...currentShape, ...attrs };
            shapesMap.set(id, updatedShape);
        }
    }, []);

    const deleteShapeInYjs = useCallback((id: string) => {
        if (!yjsManager.isConnected) return;
        yjsManager.shapesMap.delete(id);
    }, []);

    const undo = useCallback(() => {
        if (!yjsManager.isConnected) return;
        yjsManager.undoManager.undo();
    }, []);

    const redo = useCallback(() => {
        if (!yjsManager.isConnected) return;
        yjsManager.undoManager.redo();
    }, []);

    const updateAwareness = useCallback((x: number, y: number) => {
        const awareness = yjsManager.getAwareness();
        if (awareness) {
            awareness.setLocalStateField('cursor', { x, y });
        }
    }, []);

    const updateShapesInYjs = useCallback((updates: Record<string, Partial<Shape>>) => {
        if (!yjsManager.isConnected) return;
        const ydoc = yjsManager.ydoc;
        const shapesMap = yjsManager.shapesMap;
        
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
        isConnected: yjsManager.isConnected,
        currentRoomId: yjsManager.roomId,
    };
};
