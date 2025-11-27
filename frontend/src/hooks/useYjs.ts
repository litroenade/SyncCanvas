import { useEffect } from 'react';
import { useCanvasStore, Shape } from '../stores/useCanvasStore';
import { shapesMap, undoManager, provider, ydoc } from '../lib/yjs';

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

export const useYjs = () => {
    const { setShapes, setCursors } = useCanvasStore();

    useEffect(() => {
        // 从 Yjs 同步到 Store
        const observer = () => {
            const shapes = shapesMap.toJSON() as Record<string, Shape>;
            setShapes(shapes);
        };

        shapesMap.observe(observer);

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
        };
    }, [setShapes, setCursors]);

    // 更新 Yjs 的操作
    const addShapeToYjs = (shape: Shape) => {
        shapesMap.set(shape.id, shape);
    };

    const updateShapeInYjs = (id: string, attrs: Partial<Shape>) => {
        const currentShape = shapesMap.get(id) as Shape | undefined;
        if (currentShape) {
            const updatedShape = { ...currentShape, ...attrs };
            shapesMap.set(id, updatedShape);
        }
    };

    const deleteShapeInYjs = (id: string) => {
        shapesMap.delete(id);
    };

    const undo = () => {
        undoManager.undo();
    };

    const redo = () => {
        undoManager.redo();
    };

    const updateAwareness = (x: number, y: number) => {
        provider.awareness.setLocalStateField('cursor', { x, y });
    };

    const updateShapesInYjs = (updates: Record<string, Partial<Shape>>) => {
        ydoc.transact(() => {
            Object.entries(updates).forEach(([id, attrs]) => {
                const currentShape = shapesMap.get(id) as Shape | undefined;
                if (currentShape) {
                    const updatedShape = { ...currentShape, ...attrs };
                    shapesMap.set(id, updatedShape);
                }
            });
        });
    };

    return {
        addShape: addShapeToYjs,
        updateShape: updateShapeInYjs,
        updateShapes: updateShapesInYjs,
        deleteShape: deleteShapeInYjs,
        undo,
        redo,
        updateAwareness
    };
};
