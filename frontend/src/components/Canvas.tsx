/**
 * 模块名称：Canvas
 * 主要功能：画布组件
 * 
 * 主绘图区域，处理图形渲染、交互（拖拽、缩放、选择、绘制）以及与 Yjs 的同步。
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Stage, Layer, Transformer, Rect } from 'react-konva';
import { useCanvasStore, Shape, ToolType } from '../stores/useCanvasStore';
import { useYjs } from '../hooks/useYjs';
import { Grid } from './Grid';
import { Toolbar } from './Toolbar';
import { Sidebar } from './Sidebar';
import { useThemeStore } from '../stores/useThemeStore';
import { cn } from '../lib/utils';
import { PropertiesPanel } from './PropertiesPanel';
import { Cursors } from './Cursors';
import { ZoomControls } from './ZoomControls';
import { CollaboratorList } from './CollaboratorList';
import { BrushCursor } from './BrushCursor';
import { isShapeIntersecting, getWorldPos } from '../lib/geometry';
import { ShapeView } from './ShapeView';

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
        setScale, setOffset, setSelectedId, setSelectedIds, toggleSelection, clearSelection,
        setIsDrawing, setCurrentTool, setCurrentStrokeColor, setCurrentFillColor
    } = useCanvasStore();
    const { addShape, updateShape, deleteShape, isConnected, isSynced } = useYjs(roomId);
    const { theme } = useThemeStore();
    const shapeRefs = useRef<Record<string, any>>({});
    const trRef = useRef<any>(null);
    const stageRef = useRef<any>(null);

    // 绘制状态 - 使用 ref 存储实时数据，state 用于触发渲染
    const drawStartRef = useRef<{ x: number; y: number } | null>(null);
    const lastPointerPositionRef = useRef<{ x: number; y: number } | null>(null);
    const dragStartPosRef = useRef<Record<string, { x: number; y: number }>>({});
    const drawingShapeRef = useRef<Shape | null>(null);
    const [drawingShape, setDrawingShape] = useState<Shape | null>(null);
    const rafIdRef = useRef<number | null>(null);

    // 文本编辑状态
    const [editingTextId, setEditingTextId] = useState<string | null>(null);
    const [editText, setEditText] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // 框选状态
    const [isSelecting, setIsSelecting] = useState(false);
    const [selectionBox, setSelectionBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
    const selectionStartRef = useRef<{ x: number; y: number } | null>(null);

    // 监听键盘事件 (只保留 Escape 和 Delete)
    useEffect(() => {
        if (isGuest) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (editingTextId) return;

            const activeElement = document.activeElement;
            const isInputActive = activeElement?.tagName === 'INPUT' || activeElement?.tagName === 'TEXTAREA';
            if (isInputActive) return;

            // Delete/Backspace 删除选中的图形
            if ((e.key === 'Delete' || e.key === 'Backspace') && selectedIds.length > 0) {
                selectedIds.forEach(id => deleteShape(id));
                clearSelection();
            }

            // Escape 取消当前绘制或选择
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
    }, [selectedIds, deleteShape, clearSelection, editingTextId, isGuest, isDrawing, drawingShape, setCurrentTool, setIsDrawing]);

    // 自动聚焦文本框
    useEffect(() => {
        if (editingTextId && textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.select();
        }
    }, [editingTextId]);

    // 选中图形时，同步颜色到全局状态，保持 UI 一致
    useEffect(() => {
        if (selectedIds.length === 1) {
            const shape = shapes[selectedIds[0]];
            if (shape) {
                if (shape.strokeColor) setCurrentStrokeColor(shape.strokeColor);
                if (shape.fill) setCurrentFillColor(shape.fill);
                if (shape.strokeWidth) useCanvasStore.getState().setCurrentStrokeWidth(shape.strokeWidth);
            }
        }
    }, [selectedIds, shapes, setCurrentStrokeColor, setCurrentFillColor]);

    // 更新 Transformer 选中节点
    useEffect(() => {
        if (!trRef.current) return;

        if (currentTool === 'select' && selectedIds.length > 0) {
            const nodes = selectedIds
                .map(id => shapeRefs.current[id])
                .filter(node => node !== undefined);
            
            if (nodes.length > 0) {
                trRef.current.nodes(nodes);
                trRef.current.getLayer()?.batchDraw();
            } else {
                trRef.current.nodes([]);
            }
        } else {
            trRef.current.nodes([]);
            trRef.current.getLayer()?.batchDraw();
        }
    }, [selectedIds, currentTool]);

    const handleShapeDragStart = useCallback((id: string) => {
        if (isGuest || currentTool !== 'select') return;
        if (selectedIds.includes(id)) {
            const initialPos: Record<string, { x: number; y: number }> = {};
            selectedIds.forEach(sid => {
                const node = shapeRefs.current[sid];
                if (node) {
                    initialPos[sid] = { x: node.x(), y: node.y() };
                }
            });
            dragStartPosRef.current = initialPos;
        }
    }, [isGuest, currentTool, selectedIds]);

    const handleShapeDragMove = useCallback((id: string, e: any) => {
        if (isGuest || currentTool !== 'select') return;
        if (selectedIds.includes(id) && selectedIds.length > 1) {
            const startPos = dragStartPosRef.current[id];
            if (!startPos) return;

            const dx = e.target.x() - startPos.x;
            const dy = e.target.y() - startPos.y; 

            selectedIds.forEach(sid => {
                if (sid !== id) {
                    const node = shapeRefs.current[sid];
                    const init = dragStartPosRef.current[sid];
                    if (node && init) {
                        node.x(init.x + dx);
                        node.y(init.y + dy);
                    }
                }
            });
            
            // 使用 batchDraw 提高拖拽平滑度
            e.target.getLayer()?.batchDraw();
        }
    }, [isGuest, currentTool, selectedIds]);

    const handleDragEnd = useCallback((id: string, e: any) => {
        if (isGuest) return;

        if (selectedIds.includes(id) && selectedIds.length > 1) {
            const startPos = dragStartPosRef.current[id];
            if (startPos) {
                const dx = e.target.x() - startPos.x;
                const dy = e.target.y() - startPos.y;

                selectedIds.forEach(sid => {
                    const init = dragStartPosRef.current[sid];
                    if (init) {
                        updateShape(sid, {
                            x: init.x + dx,
                            y: init.y + dy,
                        });
                    }
                });
            }
        } else {
            updateShape(id, {
                x: e.target.x(),
                y: e.target.y(),
            });
        }
        dragStartPosRef.current = {};
    }, [isGuest, updateShape, selectedIds]);

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
    /**
     * 开始绘制 - 只创建本地临时图形
     */
    const handleDrawStart = useCallback((e: any) => {
        if (isGuest) return;

        const stage = e.target.getStage();
        const pos = getWorldPos(stage);
        if (!pos) return;

        // select 工具：点击空白启动框选
        if (currentTool === 'select') {
            const clickedOnEmpty = e.target === stage;
            if (clickedOnEmpty) {
                if (!e.evt.shiftKey) {
                    clearSelection();
                }
                setEditingTextId(null);
                // 启动框选
                selectionStartRef.current = pos;
                setIsSelecting(true);
                setSelectionBox({ x: pos.x, y: pos.y, width: 0, height: 0 });
            }
            return;
        }

        // eraser 工具：drag start
        if (currentTool === 'eraser') {
            if (e.evt.buttons === 1) {
                lastPointerPositionRef.current = pos;
            }
            return;
        }

        // hand 工具：不处理
        if (currentTool === 'hand') return;

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

        drawingShapeRef.current = newShape;
        setDrawingShape(newShape);
    }, [isGuest, currentTool, shapes, addShape, setSelectedId, setCurrentTool, currentStrokeColor, currentStrokeWidth, currentFillColor, clearSelection, setIsDrawing]);

    /**
     * 绘制移动 / 橡皮擦移动 / 框选移动
     */
    const handleDrawMove = useCallback((e: any) => {
        if (isGuest) return;
        const stage = e.target.getStage();
        const pos = getWorldPos(stage);
        if (!pos) return;

        // Eraser
        if (currentTool === 'eraser') {
            if (e.evt.buttons === 1) {
                const lastPos = lastPointerPositionRef.current || pos;
                // 查找相交的图形并删除
                Object.values(shapes).forEach(shape => {
                    if (isShapeIntersecting(shape, lastPos, pos)) {
                        deleteShape(shape.id);
                    }
                });
                lastPointerPositionRef.current = pos;
            } else {
                lastPointerPositionRef.current = null;
            }
            return;
        }

        // Selecting
        if (isSelecting && selectionBox && selectionStartRef.current) {
            const start = selectionStartRef.current;
            const width = pos.x - start.x;
            const height = pos.y - start.y;

            setSelectionBox({
                x: width < 0 ? start.x + width : start.x,
                y: height < 0 ? start.y + height : start.y,
                width: Math.abs(width),
                height: Math.abs(height),
            });
            return;
        }

        // Drawing
        if (!isDrawing || !drawingShapeRef.current || !drawStartRef.current) return;

        const start = drawStartRef.current;
        const currentShape = drawingShapeRef.current;

        if (currentShape.type === 'freedraw') {
            const points = currentShape.points || [];
            drawingShapeRef.current = {
                ...currentShape,
                points: [...points, pos.x, pos.y]
            };
        } else if (currentShape.type === 'line' || currentShape.type === 'arrow') {
            drawingShapeRef.current = {
                ...currentShape,
                points: [start.x, start.y, pos.x, pos.y]
            };
        } else {
            // Shapes with shift key constraint
            let width = pos.x - start.x;
            let height = pos.y - start.y;

            if (e.evt.shiftKey) {
                const s = Math.max(Math.abs(width), Math.abs(height));
                width = width >= 0 ? s : -s;
                height = height >= 0 ? s : -s;
            }

            drawingShapeRef.current = {
                ...currentShape,
                x: width < 0 ? start.x + width : start.x,
                y: height < 0 ? start.y + height : start.y,
                width: Math.abs(width),
                height: Math.abs(height),
            };
        }

        // 渲染循环
        if (rafIdRef.current === null) {
            rafIdRef.current = requestAnimationFrame(() => {
                setDrawingShape(drawingShapeRef.current);
                rafIdRef.current = null;
            });
        }
    }, [isGuest, currentTool, isSelecting, selectionBox, isDrawing, shapes, deleteShape]);

    /**
     * 结束绘制/框选 - 最终同步到 Yjs
     */
    const handleDrawEnd = useCallback((e?: any) => {
        // 框选结束处理
        if (isSelecting && selectionBox) {
            // 计算框选范围内的所有图形
            const selectedShapeIds = Object.values(shapes)
                .filter(shape => {
                    const shapeLeft = shape.x;
                    const shapeTop = shape.y;
                    const shapeRight = shape.x + (shape.width || 0);
                    const shapeBottom = shape.y + (shape.height || 0);

                    const boxLeft = selectionBox.x;
                    const boxTop = selectionBox.y;
                    const boxRight = selectionBox.x + selectionBox.width;
                    const boxBottom = selectionBox.y + selectionBox.height;

                    // 检查图形是否与框选矩形相交
                    return !(shapeRight < boxLeft || shapeLeft > boxRight || shapeBottom < boxTop || shapeTop > boxBottom);
                })
                .map(shape => shape.id);

            if (selectedShapeIds.length > 0) {
                if (e?.evt?.shiftKey) {
                    const newSet = new Set([...selectedIds, ...selectedShapeIds]);
                    setSelectedIds(Array.from(newSet));
                } else {
                    setSelectedIds(selectedShapeIds);
                }
            }

            // 清理框选状态
            setIsSelecting(false);
            setSelectionBox(null);
            selectionStartRef.current = null;
            return;
        }

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
    }, [isDrawing, isSelecting, selectionBox, shapes, addShape, setSelectedId, setSelectedIds, setIsDrawing, selectedIds]);

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
    // 获取 Stage 的 cursor 样式
    const getStageCursor = () => {
        switch (currentTool) {
            case 'hand': return 'grab';
            case 'text': return 'text';
            case 'select': return 'default';
            // 画笔和橡皮擦使用自定义光标，隐藏系统光标
            case 'eraser': return 'none';
            case 'freedraw': return 'none';
            default: return 'crosshair';
        }
    };



    return (
        <div
            className={cn("w-full h-screen overflow-hidden relative", theme === 'dark' ? "bg-[#121212]" : "bg-gray-100")}
            style={{ cursor: getStageCursor() }}
        >
            <BrushCursor />
            {!isGuest && <Toolbar />}
            <Sidebar onExport={handleExport} roomId={roomId} />
            {!isGuest && <PropertiesPanel />}

            {/* 缩放控制栏 - 左下角 */}
            <div className="fixed bottom-4 left-4 z-50">
                <ZoomControls />
            </div>

            {/* 协作者列表 - 右上角 */}
            <CollaboratorList />

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
                draggable={currentTool === 'hand'}
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
                            if (editingTextId === shape.id) return null;
                            return (
                                <ShapeView
                                    key={shape.id}
                                    shape={shape}
                                    isGuest={isGuest}
                                    currentTool={currentTool}
                                    onShapeClick={handleShapeClick}
                                    onDragStart={handleShapeDragStart}
                                    onDragMove={handleShapeDragMove}
                                    onDragEnd={handleDragEnd}
                                    onTextDblClick={handleTextDblClick}
                                    shapeRef={(node) => {
                                        if (node) shapeRefs.current[shape.id] = node;
                                    }}
                                />
                            );
                        })}

                    {/* 渲染正在绘制的临时图形 */}
                    {drawingShape && (
                        <ShapeView
                            shape={drawingShape}
                            isPreview={true}
                        />
                    )}

                    {/* 渲染框选矩形 */}
                    {isSelecting && selectionBox && (
                        <Rect
                            x={selectionBox.x}
                            y={selectionBox.y}
                            width={selectionBox.width}
                            height={selectionBox.height}
                            fill="rgba(59, 130, 246, 0.1)"
                            stroke="#3b82f6"
                            strokeWidth={1}
                            dash={[5, 5]}
                            listening={false}
                        />
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


