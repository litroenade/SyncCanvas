/**
 * 模块名称：Canvas
 * 主要功能：画布组件
 * 
 * 主绘图区域，处理图形渲染、交互（拖拽、缩放、选择、绘制）以及与 Yjs 的同步。
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Stage, Layer, Rect, Circle, Text, Arrow, Line, Image as KonvaImage, Transformer } from 'react-konva';
import useImage from 'use-image';
import { useCanvasStore, Shape, ToolType } from '../stores/useCanvasStore';
import { useYjs } from '../hooks/useYjs';
import { Grid } from './Grid';
import { Toolbar } from './Toolbar';
import { Sidebar } from './Sidebar';
import { useThemeStore } from '../stores/useThemeStore';
import { cn } from '../lib/utils';
import { PropertiesPanel } from './PropertiesPanel';
import { Cursors } from './Cursors';

/**
 * 获取鼠标在画布世界坐标系中的位置
 * @param stage - Konva Stage 实例
 * @returns 世界坐标点 {x, y} 或 null
 */
const getWorldPos = (stage: any): { x: number; y: number } | null => {
    const pointer = stage.getPointerPosition();
    if (!pointer) return null;
    const transform = stage.getAbsoluteTransform().copy();
    transform.invert();
    return transform.point(pointer);
};

interface CanvasProps {
    /** 房间 ID */
    roomId?: string;
}

/**
 * 画布组件
 * 
 * @param roomId - 房间 ID
 */
export const Canvas: React.FC<CanvasProps> = ({ roomId }) => {
    const {
        scale, offset, shapes, selectedIds, cursors, isGuest,
        currentTool, isDrawing,
        currentFillColor, currentStrokeColor, currentStrokeWidth,
        setScale, setOffset, setSelectedId, toggleSelection, clearSelection,
        setIsDrawing, setCurrentTool
    } = useCanvasStore();
    const { addShape, updateShape, deleteShape, undo, redo, updateAwareness, isConnected, isSynced } = useYjs(roomId);
    const { theme } = useThemeStore();
    const shapeRefs = useRef<Record<string, any>>({});
    const trRef = useRef<any>(null);
    const stageRef = useRef<any>(null);

    // 绘制状态 - 使用 ref 存储实时数据，state 用于触发渲染
    const drawStartRef = useRef<{ x: number; y: number } | null>(null);
    const drawingShapeRef = useRef<Shape | null>(null);
    const [drawingShape, setDrawingShape] = useState<Shape | null>(null);
    const rafIdRef = useRef<number | null>(null);

    // 文本编辑状态
    const [editingTextId, setEditingTextId] = useState<string | null>(null);
    const [editText, setEditText] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // 监听键盘事件 (快捷键)
    useEffect(() => {
        if (isGuest) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (editingTextId) return;

            // 工具快捷键
            const toolKeys: Record<string, ToolType> = {
                'v': 'select', '1': 'select',
                'h': 'hand', '2': 'hand',
                'r': 'rect', '3': 'rect',
                'o': 'circle', '4': 'circle',
                'd': 'diamond', '5': 'diamond',
                'a': 'arrow', '6': 'arrow',
                'l': 'line', '7': 'line',
                'p': 'freedraw', '8': 'freedraw',
                't': 'text', '9': 'text',
                'e': 'eraser',
            };

            if (toolKeys[e.key.toLowerCase()] && !e.ctrlKey && !e.metaKey) {
                setCurrentTool(toolKeys[e.key.toLowerCase()]);
                e.preventDefault();
                return;
            }

            if ((e.key === 'Delete' || e.key === 'Backspace') && selectedIds.length > 0) {
                selectedIds.forEach(id => deleteShape(id));
                clearSelection();
            }

            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                if (e.shiftKey) {
                    redo();
                } else {
                    undo();
                }
                e.preventDefault();
            }

            if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
                redo();
                e.preventDefault();
            }

            // Escape 取消当前绘制
            if (e.key === 'Escape') {
                if (isDrawing && drawingShape) {
                    setDrawingShape(null);
                    setIsDrawing(false);
                }
                clearSelection();
                setCurrentTool('select');
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedIds, deleteShape, clearSelection, undo, redo, editingTextId, isGuest, isDrawing, drawingShape, setCurrentTool, setIsDrawing]);

    // 自动聚焦文本框
    useEffect(() => {
        if (editingTextId && textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.select();
        }
    }, [editingTextId]);

    // 更新 Transformer 选中节点
    useEffect(() => {
        if (trRef.current && currentTool === 'select') {
            const nodes = selectedIds
                .map(id => shapeRefs.current[id])
                .filter(node => node !== undefined);
            trRef.current.nodes(nodes);
            trRef.current.getLayer()?.batchDraw();
        } else if (trRef.current) {
            trRef.current.nodes([]);
        }
    }, [selectedIds, currentTool]);

    const handleDragEnd = useCallback((id: string, e: any) => {
        if (isGuest) return;
        updateShape(id, {
            x: e.target.x(),
            y: e.target.y(),
        });
    }, [isGuest, updateShape]);

    const handleSelect = useCallback((id: string | null, e?: any) => {
        if (isGuest || currentTool !== 'select') return;

        if (!id) {
            clearSelection();
            setEditingTextId(null);
            return;
        }

        if (e && (e.evt?.shiftKey || e.evt?.ctrlKey || e.evt?.metaKey)) {
            toggleSelection(id);
        } else {
            setSelectedId(id);
        }
    }, [isGuest, currentTool, clearSelection, toggleSelection, setSelectedId]);

    const handleTransformEnd = useCallback(() => {
        if (isGuest) return;
        const nodes = trRef.current?.nodes() || [];
        nodes.forEach((node: any) => {
            const scaleX = node.scaleX();
            const scaleY = node.scaleY();
            node.scaleX(1);
            node.scaleY(1);

            const shapeId = Object.keys(shapeRefs.current).find(key => shapeRefs.current[key] === node);
            if (shapeId) {
                updateShape(shapeId, {
                    x: node.x(),
                    y: node.y(),
                    width: Math.max(5, node.width() * scaleX),
                    height: Math.max(5, node.height() * scaleY),
                    rotation: node.rotation(),
                });
            }
        });
    }, [isGuest, updateShape]);

    const handleExport = useCallback(() => {
        if (!stageRef.current) return;
        const stage = stageRef.current;
        if (trRef.current) trRef.current.nodes([]);

        const dataURL = stage.toDataURL({ pixelRatio: 2 });
        const link = document.createElement('a');
        link.download = 'sync-canvas-export.png';
        link.href = dataURL;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, []);

    const handleTextDblClick = useCallback((id: string, text: string) => {
        if (isGuest) return;
        setEditingTextId(id);
        setEditText(text);
    }, [isGuest]);

    const handleTextBlur = useCallback(() => {
        if (editingTextId) {
            updateShape(editingTextId, { text: editText });
            setEditingTextId(null);
        }
    }, [editingTextId, editText, updateShape]);

    // ==================== 核心绘制逻辑（本地状态 + 最终同步）====================

    /**
     * 开始绘制 - 只创建本地临时图形
     */
    const handleDrawStart = useCallback((e: any) => {
        if (isGuest) return;

        const stage = e.target.getStage();
        const pos = getWorldPos(stage);
        if (!pos) return;

        // select 工具：点击空白取消选择
        if (currentTool === 'select') {
            const clickedOnEmpty = e.target === stage;
            if (clickedOnEmpty) {
                clearSelection();
                setEditingTextId(null);
            }
            return;
        }

        // hand 工具：不处理（Stage 的 draggable 会处理）
        if (currentTool === 'hand') return;

        // eraser 工具：在 shape 的 onClick 里处理
        if (currentTool === 'eraser') return;

        // 绘制工具
        const drawTools: ToolType[] = ['rect', 'circle', 'diamond', 'arrow', 'line', 'freedraw', 'text'];
        if (!drawTools.includes(currentTool)) return;

        // text 工具：直接创建文本并同步
        if (currentTool === 'text') {
            const id = uuidv4();
            const newShape: Shape = {
                id,
                type: 'text',
                x: pos.x,
                y: pos.y,
                text: '双击编辑',
                fill: currentStrokeColor,
                strokeColor: currentStrokeColor,
            };
            addShape(newShape);
            setSelectedId(id);
            setCurrentTool('select');
            setTimeout(() => {
                setEditingTextId(id);
                setEditText('双击编辑');
            }, 50);
            return;
        }

        // 记录起始点
        drawStartRef.current = pos;
        setIsDrawing(true);

        const id = uuidv4();
        let newShape: Shape;

        if (currentTool === 'freedraw') {
            newShape = {
                id,
                type: 'freedraw',
                x: 0,
                y: 0,
                points: [pos.x, pos.y],
                strokeColor: currentStrokeColor,
                strokeWidth: currentStrokeWidth,
                fill: 'transparent',
            };
        } else if (currentTool === 'arrow' || currentTool === 'line') {
            newShape = {
                id,
                type: currentTool,
                x: 0,
                y: 0,
                points: [pos.x, pos.y, pos.x, pos.y],
                strokeColor: currentStrokeColor,
                strokeWidth: currentStrokeWidth,
                fill: currentTool === 'arrow' ? currentStrokeColor : 'transparent',
            };
        } else {
            newShape = {
                id,
                type: currentTool as 'rect' | 'circle' | 'diamond',
                x: pos.x,
                y: pos.y,
                width: 1,
                height: 1,
                fill: currentFillColor,
                strokeColor: currentStrokeColor,
                strokeWidth: currentStrokeWidth,
            };
        }

        // 同时设置 ref 和 state
        drawingShapeRef.current = newShape;
        setDrawingShape(newShape);
        console.log('Draw start:', newShape);
    }, [isGuest, currentTool, currentFillColor, currentStrokeColor, currentStrokeWidth, addShape, clearSelection, setSelectedId, setCurrentTool, setIsDrawing]);

    /**
     * 绘制中 - 使用 RAF 优化渲染
     */
    const handleDrawMove = useCallback((e: any) => {
        const stage = e.target.getStage();
        const pos = getWorldPos(stage);

        // 更新光标位置
        if (pos) {
            updateAwareness(pos.x, pos.y);
        }

        // 非绘制状态，跳过
        const shape = drawingShapeRef.current;
        if (!isDrawing || !shape || !drawStartRef.current || !pos) return;

        const start = drawStartRef.current;

        // 更新 ref（不触发渲染）
        if (shape.type === 'freedraw') {
            const points = shape.points || [];
            const lastX = points[points.length - 2];
            const lastY = points[points.length - 1];
            const dist = Math.hypot(pos.x - lastX, pos.y - lastY);

            // 距离阈值优化
            if (dist > 2) {
                drawingShapeRef.current = {
                    ...shape,
                    points: [...points, pos.x, pos.y]
                };
            }
        } else if (shape.type === 'arrow' || shape.type === 'line') {
            drawingShapeRef.current = {
                ...shape,
                points: [start.x, start.y, pos.x, pos.y]
            };
        } else if (shape.type === 'rect' || shape.type === 'diamond') {
            const width = pos.x - start.x;
            const height = pos.y - start.y;
            drawingShapeRef.current = {
                ...shape,
                x: width < 0 ? pos.x : start.x,
                y: height < 0 ? pos.y : start.y,
                width: Math.abs(width),
                height: Math.abs(height),
            };
        } else if (shape.type === 'circle') {
            const width = pos.x - start.x;
            const height = pos.y - start.y;
            const size = Math.max(Math.abs(width), Math.abs(height));
            drawingShapeRef.current = {
                ...shape,
                x: start.x,
                y: start.y,
                width: size,
                height: size,
            };
        }

        // 使用 RAF 批量更新 state（触发渲染）
        if (rafIdRef.current === null) {
            rafIdRef.current = requestAnimationFrame(() => {
                setDrawingShape(drawingShapeRef.current);
                rafIdRef.current = null;
            });
        }
    }, [isDrawing, updateAwareness]);

    /**
     * 结束绘制 - 最终同步到 Yjs
     */
    const handleDrawEnd = useCallback(() => {
        // 取消挂起的 RAF
        if (rafIdRef.current !== null) {
            cancelAnimationFrame(rafIdRef.current);
            rafIdRef.current = null;
        }

        const shape = drawingShapeRef.current;
        if (!isDrawing || !shape) return;

        // 检查图形是否太小
        const isTooSmall =
            (shape.type === 'freedraw' && (shape.points?.length || 0) < 6) ||
            ((shape.type === 'rect' || shape.type === 'circle' || shape.type === 'diamond') &&
                ((shape.width || 0) < 5 || (shape.height || 0) < 5)) ||
            ((shape.type === 'arrow' || shape.type === 'line') && shape.points &&
                Math.hypot(shape.points[2] - shape.points[0], shape.points[3] - shape.points[1]) < 5);

        if (!isTooSmall) {
            // 同步到 Yjs
            addShape(shape);
            setSelectedId(shape.id);
        }

        // 清理状态
        drawingShapeRef.current = null;
        setDrawingShape(null);
        setIsDrawing(false);
        drawStartRef.current = null;
    }, [isDrawing, addShape, setSelectedId, setIsDrawing]);

    /**
     * 处理图形点击（用于 eraser 和 select）
     */
    const handleShapeClick = useCallback((id: string, e: any) => {
        if (currentTool === 'eraser') {
            deleteShape(id);
            e.cancelBubble = true;
        } else if (currentTool === 'select') {
            handleSelect(id, e);
        }
    }, [currentTool, deleteShape, handleSelect]);

    // 获取 Stage 的 cursor 样式
    const getStageCursor = () => {
        switch (currentTool) {
            case 'hand': return 'grab';
            case 'eraser': return 'crosshair';
            case 'text': return 'text';
            case 'freedraw': return 'crosshair';
            case 'select': return 'default';
            default: return 'crosshair';
        }
    };

    return (
        <div
            className={cn("w-full h-screen overflow-hidden relative", theme === 'dark' ? "bg-[#121212]" : "bg-gray-100")}
            style={{ cursor: getStageCursor() }}
        >
            {!isGuest && <Toolbar />}
            <Sidebar onExport={handleExport} roomId={roomId} />
            {!isGuest && <PropertiesPanel />}

            {/* 连接状态指示器 */}
            <div className={cn(
                "absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-medium z-50",
                isConnected
                    ? (isSynced ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700")
                    : "bg-red-100 text-red-700"
            )}>
                {isConnected
                    ? (isSynced ? "● 已同步" : "◐ 同步中...")
                    : "○ 连接中..."}
            </div>

            {/* 渲染远程光标 */}
            <Cursors cursors={
                Object.fromEntries(Object.entries(cursors).map(([id, cursor]) => [
                    id,
                    {
                        ...cursor,
                        x: cursor.x * scale + offset.x,
                        y: cursor.y * scale + offset.y
                    }
                ]))
            } />

            {/* 文本编辑框 */}
            {editingTextId && shapes[editingTextId] && (
                <textarea
                    ref={textareaRef}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onBlur={handleTextBlur}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleTextBlur();
                        }
                        if (e.key === 'Escape') {
                            setEditingTextId(null);
                        }
                    }}
                    style={{
                        position: 'absolute',
                        left: shapes[editingTextId].x * scale + offset.x,
                        top: shapes[editingTextId].y * scale + offset.y,
                        fontSize: `${24 * scale}px`,
                        color: shapes[editingTextId].fill || shapes[editingTextId].strokeColor,
                        background: 'transparent',
                        border: '2px solid #3b82f6',
                        borderRadius: '4px',
                        outline: 'none',
                        resize: 'none',
                        zIndex: 100,
                        minWidth: '100px',
                        minHeight: '30px',
                        padding: '4px 8px',
                        fontFamily: 'inherit',
                    }}
                />
            )}

            <Stage
                ref={stageRef}
                width={window.innerWidth}
                height={window.innerHeight}
                draggable={currentTool === 'hand' || currentTool === 'select'}
                scaleX={scale}
                scaleY={scale}
                x={offset.x}
                y={offset.y}
                onMouseDown={handleDrawStart}
                onMouseMove={handleDrawMove}
                onMouseUp={handleDrawEnd}
                onMouseLeave={handleDrawEnd}
                onTouchStart={handleDrawStart}
                onTouchMove={handleDrawMove}
                onTouchEnd={handleDrawEnd}
                onDragEnd={(e) => {
                    if (e.target === e.currentTarget) {
                        setOffset({ x: e.target.x(), y: e.target.y() });
                    }
                }}
                onWheel={(e) => {
                    e.evt.preventDefault();
                    const scaleBy = 1.1;
                    const oldScale = scale;
                    const pointer = e.target.getStage()?.getPointerPosition();
                    if (!pointer) return;

                    const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
                    const clampedScale = Math.max(0.1, Math.min(5, newScale));

                    // 以鼠标位置为中心缩放
                    const mousePointTo = {
                        x: (pointer.x - offset.x) / oldScale,
                        y: (pointer.y - offset.y) / oldScale,
                    };
                    const newOffset = {
                        x: pointer.x - mousePointTo.x * clampedScale,
                        y: pointer.y - mousePointTo.y * clampedScale,
                    };

                    setScale(clampedScale);
                    setOffset(newOffset);
                }}
            >
                <Layer>
                    <Grid />
                    {Object.values(shapes)
                        .sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0))
                        .map((shape) => {
                            const isEditing = editingTextId === shape.id;

                            if (isEditing) return null;

                            const commonProps = {
                                key: shape.id,
                                id: shape.id,
                                ref: (node: any) => {
                                    if (node) shapeRefs.current[shape.id] = node;
                                },
                                x: shape.x,
                                y: shape.y,
                                rotation: shape.rotation || 0,
                                opacity: shape.opacity ?? 1,
                                draggable: !isGuest && currentTool === 'select',
                                onClick: (e: any) => handleShapeClick(shape.id, e),
                                onTap: (e: any) => handleShapeClick(shape.id, e),
                                onDragEnd: (e: any) => handleDragEnd(shape.id, e),
                                stroke: shape.strokeColor || '#1e1e1e',
                                strokeWidth: shape.strokeWidth || 2,
                            };

                            if (shape.type === 'rect') {
                                return (
                                    <Rect
                                        {...commonProps}
                                        width={shape.width}
                                        height={shape.height}
                                        fill={shape.fill}
                                        cornerRadius={shape.cornerRadius || 0}
                                    />
                                );
                            } else if (shape.type === 'circle') {
                                return (
                                    <Circle
                                        {...commonProps}
                                        // 圆心在 (x, y)，半径为 width/2
                                        radius={(shape.width || 100) / 2}
                                        fill={shape.fill}
                                    />
                                );
                            } else if (shape.type === 'diamond') {
                                // 菱形用 Line 绘制
                                const w = shape.width || 100;
                                const h = shape.height || 100;
                                return (
                                    <Line
                                        {...commonProps}
                                        points={[w / 2, 0, w, h / 2, w / 2, h, 0, h / 2]}
                                        closed
                                        fill={shape.fill}
                                    />
                                );
                            } else if (shape.type === 'text') {
                                return (
                                    <Text
                                        {...commonProps}
                                        text={shape.text}
                                        fontSize={24}
                                        fill={shape.fill || shape.strokeColor}
                                        onDblClick={() => handleTextDblClick(shape.id, shape.text || '')}
                                        onDblTap={() => handleTextDblClick(shape.id, shape.text || '')}
                                    />
                                );
                            } else if (shape.type === 'arrow') {
                                return (
                                    <Arrow
                                        {...commonProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || [0, 0, 100, 0]}
                                        pointerLength={12}
                                        pointerWidth={12}
                                        fill={shape.strokeColor || '#1e1e1e'}
                                    />
                                );
                            } else if (shape.type === 'line') {
                                return (
                                    <Line
                                        {...commonProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || [0, 0, 100, 0]}
                                    />
                                );
                            } else if (shape.type === 'freedraw') {
                                return (
                                    <Line
                                        {...commonProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || []}
                                        tension={0.5}
                                        lineCap="round"
                                        lineJoin="round"
                                        globalCompositeOperation="source-over"
                                    />
                                );
                            } else if (shape.type === 'image' && shape.imageUrl) {
                                return (
                                    <URLImage
                                        {...commonProps}
                                        src={shape.imageUrl}
                                        width={shape.width}
                                        height={shape.height}
                                    />
                                );
                            }
                            return null;
                        })}

                    {/* 渲染正在绘制的临时图形 */}
                    {drawingShape && (
                        (() => {
                            const shape = drawingShape;
                            const tempProps = {
                                key: 'drawing-temp',
                                x: shape.x,
                                y: shape.y,
                                stroke: shape.strokeColor || '#1e1e1e',
                                strokeWidth: shape.strokeWidth || 2,
                                opacity: 0.8,
                                listening: false, // 不响应事件
                            };

                            if (shape.type === 'rect') {
                                return (
                                    <Rect
                                        {...tempProps}
                                        width={shape.width}
                                        height={shape.height}
                                        fill={shape.fill}
                                    />
                                );
                            } else if (shape.type === 'circle') {
                                return (
                                    <Circle
                                        {...tempProps}
                                        radius={(shape.width || 1) / 2}
                                        fill={shape.fill}
                                    />
                                );
                            } else if (shape.type === 'diamond') {
                                const w = shape.width || 1;
                                const h = shape.height || 1;
                                return (
                                    <Line
                                        {...tempProps}
                                        points={[w / 2, 0, w, h / 2, w / 2, h, 0, h / 2]}
                                        closed
                                        fill={shape.fill}
                                    />
                                );
                            } else if (shape.type === 'arrow') {
                                return (
                                    <Arrow
                                        {...tempProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || [0, 0, 0, 0]}
                                        pointerLength={12}
                                        pointerWidth={12}
                                        fill={shape.strokeColor || '#1e1e1e'}
                                    />
                                );
                            } else if (shape.type === 'line') {
                                return (
                                    <Line
                                        {...tempProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || [0, 0, 0, 0]}
                                    />
                                );
                            } else if (shape.type === 'freedraw') {
                                return (
                                    <Line
                                        {...tempProps}
                                        x={0}
                                        y={0}
                                        points={shape.points || []}
                                        tension={0.5}
                                        lineCap="round"
                                        lineJoin="round"
                                    />
                                );
                            }
                            return null;
                        })()
                    )}

                    {!isGuest && currentTool === 'select' && (
                        <Transformer
                            ref={trRef}
                            boundBoxFunc={(oldBox, newBox) => {
                                if (newBox.width < 5 || newBox.height < 5) {
                                    return oldBox;
                                }
                                return newBox;
                            }}
                            onTransformEnd={handleTransformEnd}
                        />
                    )}
                </Layer>
            </Stage>
        </div>
    );
};

// 辅助组件：用于加载和渲染图片
const URLImage = ({ src, ...props }: any) => {
    const [image] = useImage(src);
    return <KonvaImage image={image} {...props} />;
};
