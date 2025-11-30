import React from 'react';
import { Trash2, GripVertical } from 'lucide-react';
import { useCanvasStore } from '../stores/useCanvasStore';
import { useYjs } from '../hooks/useYjs';
import { cn } from '../lib/utils';
import { useThemeStore } from '../stores/useThemeStore';

export const LayersPanel: React.FC = () => {
    const { shapes, selectedIds, setSelectedId, toggleSelection } = useCanvasStore();
    const { deleteShape } = useYjs();
    const { theme } = useThemeStore();

    // Sort shapes by z-index (descending for layers list: top layer first)
    const sortedShapes = Object.values(shapes).sort((a, b) => (b.zIndex || 0) - (a.zIndex || 0));

    const handleSelect = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (e.ctrlKey || e.metaKey) {
            toggleSelection(id);
        } else {
            setSelectedId(id);
        }
    };

    const handleDelete = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        deleteShape(id);
    };

    const getIconForType = (type: string) => {
        switch (type) {
            case 'rect': return '⬜';
            case 'circle': return '⭕';
            case 'diamond': return '◇';
            case 'text': return '📝';
            case 'arrow': return '↗️';
            case 'line': return '➖';
            case 'freedraw': return '✏️';
            case 'image': return '🖼️';
            default: return '❓';
        }
    };

    if (sortedShapes.length === 0) {
        return (
            <div className={cn("p-4 text-center text-sm", theme === 'dark' ? "text-slate-500" : "text-slate-400")}>
                画布为空
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-1 p-2">
            {sortedShapes.map((shape) => (
                <div
                    key={shape.id}
                    onClick={(e) => handleSelect(shape.id, e)}
                    className={cn(
                        "group flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors border",
                        selectedIds.includes(shape.id)
                            ? "bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300"
                            : theme === 'dark'
                                ? "border-transparent hover:bg-slate-800 text-slate-300"
                                : "border-transparent hover:bg-slate-100 text-slate-700"
                    )}
                >
                    <GripVertical size={14} className={cn("opacity-0 group-hover:opacity-100 cursor-grab", theme === 'dark' ? "text-slate-600" : "text-slate-400")} />
                    <span className="text-base">{getIconForType(shape.type)}</span>
                    <span className="flex-1 truncate font-medium">
                        {shape.type === 'text' ? (shape.text || 'Text') : shape.type}
                    </span>

                    <button
                        onClick={(e) => handleDelete(shape.id, e)}
                        className={cn(
                            "opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 hover:text-red-600 transition-all",
                            theme === 'dark' ? "hover:bg-red-900/30" : ""
                        )}
                        title="删除"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            ))}
        </div>
    );
};
