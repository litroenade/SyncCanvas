import React from 'react';
import { yjsManager } from '../lib/yjs';
import { useCanvasStore, ToolType, Shape } from '../stores/useCanvasStore';
import {
    MousePointer2, Hand, Square, Circle, Diamond,
    ArrowRight, Minus, Pencil, Type, Image as ImageIcon,
    Eraser, Layout, Undo2, Redo2, Lock, Unlock
} from 'lucide-react';
import { cn } from '../lib/utils';
import { applyForceLayout } from '../lib/d3-layout';
import { useModal } from './Modal';

// 直接使用 yjsManager 的操作
const addShape = (shape: Shape) => {
    const shapesMap = yjsManager.shapesMap;
    if (!shapesMap) {
        console.warn('Yjs 未连接，无法添加图形');
        return;
    }
    shapesMap.set(shape.id, shape);
};

const updateShapes = (updates: Record<string, Partial<Shape>>) => {
    const ydoc = yjsManager.ydoc;
    const shapesMap = yjsManager.shapesMap;
    if (!ydoc || !shapesMap) {
        console.warn('Yjs 未连接，无法批量更新');
        return;
    }

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

const undo = () => {
    const undoManager = yjsManager.undoManager;
    if (!undoManager) {
        console.warn('Yjs 未连接，无法撤销');
        return;
    }
    undoManager.undo();
};

const redo = () => {
    const undoManager = yjsManager.undoManager;
    if (!undoManager) {
        console.warn('Yjs 未连接，无法重做');
        return;
    }
    undoManager.redo();
};

/**
 * 工具栏组件 - Excalidraw 风格
 * 
 * 提供工具选择和快捷操作。
 */
export const Toolbar: React.FC = () => {
    const {
        shapes, currentTool, setCurrentTool,
        currentStrokeColor, currentFillColor,
        setCurrentStrokeColor, setCurrentFillColor,
        isShortcutLocked, toggleShortcutLock
    } = useCanvasStore();
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    // 自定义弹窗
    const { showAlert, showToast, ModalRenderer } = useModal();

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const token = localStorage.getItem('token');

        // 创建 FormData
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: token ? {
                    'Authorization': `Bearer ${token}`
                } : {},
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '上传失败');
            }

            const data = await response.json();

            // 使用服务器返回的 URL
            addShape({
                id: crypto.randomUUID(),
                type: 'image',
                x: window.innerWidth / 2 - 100,
                y: window.innerHeight / 2 - 100,
                width: 200,
                height: 200,
                imageUrl: data.url
            });

            showToast('图片上传成功', 'success');
        } catch (error) {
            console.error('图片上传失败:', error);
            showAlert(error instanceof Error ? error.message : '图片上传失败', { type: 'error', title: '上传失败' });
        }

        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleAutoLayout = () => {
        const newShapes = applyForceLayout(shapes);
        updateShapes(newShapes);
    };

    const tools: { tool: ToolType; icon: any; title: string; shortcut: string }[] = [
        { tool: 'select', icon: MousePointer2, title: '选择', shortcut: 'V' },
        { tool: 'hand', icon: Hand, title: '移动画布', shortcut: 'H' },
        { tool: 'rect', icon: Square, title: '矩形', shortcut: 'R' },
        { tool: 'circle', icon: Circle, title: '圆形', shortcut: 'O' },
        { tool: 'diamond', icon: Diamond, title: '菱形', shortcut: 'D' },
        { tool: 'arrow', icon: ArrowRight, title: '箭头', shortcut: 'A' },
        { tool: 'line', icon: Minus, title: '线条', shortcut: 'L' },
        { tool: 'freedraw', icon: Pencil, title: '画笔', shortcut: 'P' },
        { tool: 'text', icon: Type, title: '文本', shortcut: 'T' },
        { tool: 'eraser', icon: Eraser, title: '橡皮擦', shortcut: 'E' },
    ];

    const ToolButton = ({
        tool,
        icon: Icon,
        title,
        shortcut,
        active
    }: {
        tool: ToolType;
        icon: any;
        title: string;
        shortcut: string;
        active: boolean;
    }) => (
        <button
            onClick={() => setCurrentTool(tool)}
            className={cn(
                "p-2.5 rounded-lg transition-all relative group",
                active
                    ? "bg-blue-500 text-white shadow-md"
                    : "text-slate-600 hover:bg-slate-100"
            )}
            title={`${title} (${shortcut})`}
        >
            <Icon size={18} strokeWidth={active ? 2.5 : 2} />
            {/* 快捷键提示 */}
            <span className="absolute -bottom-1 -right-1 text-[10px] font-mono bg-slate-200 text-slate-500 px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                {shortcut}
            </span>
        </button>
    );

    const ActionButton = ({ onClick, icon: Icon, title, className, active }: { onClick: () => void, icon: any, title: string, className?: string, active?: boolean }) => (
        <button
            onClick={onClick}
            className={cn(
                "p-2.5 rounded-lg transition-colors",
                active ? "bg-amber-100 text-amber-600" : "text-slate-600 hover:bg-slate-100",
                className
            )}
            title={title}
        >
            <Icon size={18} />
        </button>
    );

    // 预设颜色
    const presetColors = [
        'transparent', '#1e1e1e', '#e03131', '#2f9e44', '#1971c2',
        '#f08c00', '#9c36b5', '#0c8599', '#f8f9fa'
    ];

    return (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
            <div className="bg-white border border-slate-200 shadow-lg rounded-xl p-1.5 flex items-center gap-1">
                {/* 工具按钮 */}
                {tools.map(({ tool, icon, title, shortcut }) => (
                    <ToolButton
                        key={tool}
                        tool={tool}
                        icon={icon}
                        title={title}
                        shortcut={shortcut}
                        active={currentTool === tool}
                    />
                ))}

                {/* 分隔线 */}
                <div className="w-px h-8 bg-slate-200 mx-1" />

                {/* 图片上传 */}
                <ActionButton
                    onClick={() => fileInputRef.current?.click()}
                    icon={ImageIcon}
                    title="插入图片"
                />
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="image/*"
                    onChange={handleImageUpload}
                />

                {/* 自动布局 */}
                <ActionButton onClick={handleAutoLayout} icon={Layout} title="自动布局" />

                {/* 快捷键锁定 */}
                <ActionButton
                    onClick={toggleShortcutLock}
                    icon={isShortcutLocked ? Lock : Unlock}
                    title={isShortcutLocked ? "快捷键已锁定" : "快捷键已启用"}
                    active={isShortcutLocked}
                />

                {/* 分隔线 */}
                <div className="w-px h-8 bg-slate-200 mx-1" />

                {/* 撤销/重做 */}
                <ActionButton onClick={undo} icon={Undo2} title="撤销 (Ctrl+Z)" />
                <ActionButton onClick={redo} icon={Redo2} title="重做 (Ctrl+Y)" />

                {/* 分隔线 */}
                <div className="w-px h-8 bg-slate-200 mx-1" />

                {/* 描边颜色选择 */}
                <div className="flex items-center gap-1 px-1">
                    <span className="text-xs text-slate-400 mr-1">线</span>
                    {presetColors.slice(0, 5).map((color) => (
                        <button
                            key={`stroke-${color}`}
                            onClick={() => setCurrentStrokeColor(color)}
                            className={cn(
                                "w-5 h-5 rounded-full border-2 transition-transform hover:scale-110",
                                currentStrokeColor === color ? "border-blue-500 scale-110" : "border-slate-300",
                                color === 'transparent' && "bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOCIgaGVpZ2h0PSI4IiB2aWV3Qm94PSIwIDAgOCA4IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHdpZHRoPSI0IiBoZWlnaHQ9IjQiIGZpbGw9IiNjY2MiLz48cmVjdCB4PSI0IiB5PSI0IiB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjY2NjIi8+PC9zdmc+')]"
                            )}
                            style={{ backgroundColor: color === 'transparent' ? undefined : color }}
                            title={color === 'transparent' ? '透明' : color}
                        />
                    ))}
                </div>

                {/* 填充颜色选择 */}
                <div className="flex items-center gap-1 px-1">
                    <span className="text-xs text-slate-400 mr-1">填</span>
                    {presetColors.slice(0, 5).map((color) => (
                        <button
                            key={`fill-${color}`}
                            onClick={() => setCurrentFillColor(color)}
                            className={cn(
                                "w-5 h-5 rounded border-2 transition-transform hover:scale-110",
                                currentFillColor === color ? "border-blue-500 scale-110" : "border-slate-300",
                                color === 'transparent' && "bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOCIgaGVpZ2h0PSI4IiB2aWV3Qm94PSIwIDAgOCA4IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHdpZHRoPSI0IiBoZWlnaHQ9IjQiIGZpbGw9IiNjY2MiLz48cmVjdCB4PSI0IiB5PSI0IiB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjY2NjIi8+PC9zdmc+')]"
                            )}
                            style={{ backgroundColor: color === 'transparent' ? undefined : color }}
                            title={color === 'transparent' ? '透明' : color}
                        />
                    ))}
                </div>
            </div>

            {/* Modal 渲染器 */}
            <ModalRenderer />
        </div>
    );
};