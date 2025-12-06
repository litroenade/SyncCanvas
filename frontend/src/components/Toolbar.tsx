import React from 'react';
import { yjsManager } from '../lib/yjs';
import { useCanvasStore, ToolType, Shape } from '../stores/useCanvasStore';
import {
    MousePointer2, Hand, Square, Circle, Diamond,
    ArrowRight, Minus, Pencil, Type, Image as ImageIcon,
    Eraser, Layout
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

/**
 * 工具栏组件 - Excalidraw 风格
 * 
 * 简洁的工具选择栏，颜色选择通过双击工具图标触发。
 */
export const Toolbar: React.FC = () => {
    const { shapes, currentTool, setCurrentTool } = useCanvasStore();
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

    // 工具配置（无快捷键）
    const tools: { tool: ToolType; icon: any; title: string }[] = [
        { tool: 'select', icon: MousePointer2, title: '选择' },
        { tool: 'hand', icon: Hand, title: '移动画布' },
        { tool: 'rect', icon: Square, title: '矩形' },
        { tool: 'circle', icon: Circle, title: '椭圆' },
        { tool: 'diamond', icon: Diamond, title: '菱形' },
        { tool: 'arrow', icon: ArrowRight, title: '箭头' },
        { tool: 'line', icon: Minus, title: '线条' },
        { tool: 'freedraw', icon: Pencil, title: '画笔' },
        { tool: 'text', icon: Type, title: '文本' },
        { tool: 'eraser', icon: Eraser, title: '橡皮擦' },
    ];

    // 工具按钮组件 - Excalidraw 风格
    const ToolButton = ({
        tool,
        icon: Icon,
        title,
        active
    }: {
        tool: ToolType;
        icon: any;
        title: string;
        active: boolean;
    }) => (
        <button
            onClick={() => setCurrentTool(tool)}
            className={cn(
                "p-2.5 rounded-lg transition-all",
                active
                    ? "bg-violet-100 text-violet-700"
                    : "text-slate-600 hover:bg-slate-100"
            )}
            title={title}
        >
            <Icon size={18} strokeWidth={active ? 2.5 : 2} />
        </button>
    );

    // 操作按钮组件
    const ActionButton = ({ onClick, icon: Icon, title }: { onClick: () => void, icon: any, title: string }) => (
        <button
            onClick={onClick}
            className="p-2.5 rounded-lg transition-colors text-slate-600 hover:bg-slate-100"
            title={title}
        >
            <Icon size={18} />
        </button>
    );

    return (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
            <div className="bg-white border border-slate-200 shadow-lg rounded-xl p-1.5 flex items-center gap-0.5">
                {/* 工具按钮 */}
                {tools.map(({ tool, icon, title }) => (
                    <ToolButton
                        key={tool}
                        tool={tool}
                        icon={icon}
                        title={title}
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
            </div>

            {/* Modal 渲染器 */}
            <ModalRenderer />
        </div>
    );
};
