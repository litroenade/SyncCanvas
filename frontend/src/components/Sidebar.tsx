import React, { useState } from 'react';
import { Settings, ChevronLeft, ChevronRight, Layers, Grid as GridIcon, Download, Undo, Redo, ArrowUpToLine, ArrowDownToLine, Sun, Moon, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../lib/utils';
import { useYjs } from '../hooks/useYjs';
import { useCanvasStore } from '../stores/useCanvasStore';
import { useThemeStore } from '../stores/useThemeStore';
import { SettingsModal } from './SettingsModal';
import { LayersPanel } from './LayersPanel';

interface SidebarProps {
    onExport: () => void;
    roomId?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ onExport, roomId }) => {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);
    const [activePanel, setActivePanel] = useState<'layers' | 'none'>('none');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const { undo, redo, updateShape, leaveRoom } = useYjs(roomId);
    const { selectedIds, shapes, showGrid, toggleGrid: toggleGridStore, isGuest } = useCanvasStore();
    const { theme, toggleTheme } = useThemeStore();

    const handleBackToRooms = () => {
        leaveRoom();
        navigate('/rooms');
    };

    const handleBringToFront = () => {
        if (selectedIds.length === 0) return;
        const maxZ = Math.max(...Object.values(shapes).map(s => s.zIndex || 0), 0);
        selectedIds.forEach(id => {
            updateShape(id, { zIndex: maxZ + 1 });
        });
    };

    const handleSendToBack = () => {
        if (selectedIds.length === 0) return;
        const minZ = Math.min(...Object.values(shapes).map(s => s.zIndex || 0), 0);
        selectedIds.forEach(id => {
            updateShape(id, { zIndex: minZ - 1 });
        });
    };

    const togglePanel = (panel: 'layers') => {
        if (activePanel === panel) {
            setActivePanel('none');
        } else {
            setActivePanel(panel);
            setIsOpen(true);
        }
    };

    return (
        <>
            <div
                className={cn(
                    "fixed top-0 left-0 h-full border-r shadow-sm transition-all duration-300 z-40 flex flex-col",
                    isOpen ? "w-64" : "w-12",
                    theme === 'dark' ? "bg-slate-900 border-slate-700" : "bg-white border-slate-200"
                )}
            >
                {/* Toggle Button */}
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className={cn(
                        "absolute -right-3 top-6 border rounded-full p-1 shadow-sm transition-colors",
                        theme === 'dark'
                            ? "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                            : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                    )}
                >
                    {isOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
                </button>

                {/* Content */}
                <div className="flex-1 overflow-y-auto py-4">
                    {/* Menu Items */}
                    <div className="flex flex-col gap-1 px-2">
                        {/* 返回房间列表按钮 */}
                        <SidebarItem 
                            icon={Home} 
                            label="房间列表" 
                            isOpen={isOpen} 
                            onClick={handleBackToRooms} 
                            theme={theme} 
                        />
                        <div className={cn("h-px my-2 mx-2", theme === 'dark' ? "bg-slate-700" : "bg-slate-100")} />

                        {!isGuest && (
                            <>
                                <SidebarItem icon={Undo} label="撤销" isOpen={isOpen} onClick={undo} theme={theme} />
                                <SidebarItem icon={Redo} label="重做" isOpen={isOpen} onClick={redo} theme={theme} />
                                <div className={cn("h-px my-2 mx-2", theme === 'dark' ? "bg-slate-700" : "bg-slate-100")} />

                                {selectedIds.length > 0 && (
                                    <>
                                        <SidebarItem icon={ArrowUpToLine} label="置于顶层" isOpen={isOpen} onClick={handleBringToFront} theme={theme} />
                                        <SidebarItem icon={ArrowDownToLine} label="置于底层" isOpen={isOpen} onClick={handleSendToBack} theme={theme} />
                                        <div className={cn("h-px my-2 mx-2", theme === 'dark' ? "bg-slate-700" : "bg-slate-100")} />
                                    </>
                                )}

                                <SidebarItem
                                    icon={Layers}
                                    label="图层"
                                    isOpen={isOpen}
                                    onClick={() => togglePanel('layers')}
                                    active={activePanel === 'layers'}
                                    theme={theme}
                                />

                                {/* Layers Panel Content */}
                                {activePanel === 'layers' && isOpen && (
                                    <div className={cn(
                                        "mt-2 mb-2 border-t border-b py-2 max-h-96 overflow-y-auto custom-scrollbar",
                                        theme === 'dark' ? "border-slate-700" : "border-slate-100"
                                    )}>
                                        <LayersPanel />
                                    </div>
                                )}
                                <div className={cn("h-px my-2 mx-2", theme === 'dark' ? "bg-slate-700" : "bg-slate-100")} />
                            </>
                        )}

                        <SidebarItem
                            icon={GridIcon}
                            label={showGrid ? "隐藏网格" : "显示网格"}
                            isOpen={isOpen}
                            onClick={toggleGridStore}
                            active={showGrid}
                            theme={theme}
                        />

                        <SidebarItem
                            icon={theme === 'dark' ? Moon : Sun}
                            label={theme === 'dark' ? "暗色模式" : "亮色模式"}
                            isOpen={isOpen}
                            onClick={toggleTheme}
                            theme={theme}
                        />

                        <SidebarItem icon={Settings} label="设置" isOpen={isOpen} onClick={() => setIsSettingsOpen(true)} theme={theme} />
                        <SidebarItem icon={Download} label="导出" isOpen={isOpen} onClick={onExport} theme={theme} />
                    </div>
                </div>
            </div>
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </>
    );
};

const SidebarItem = ({ icon: Icon, label, isOpen, onClick, active, theme }: { icon: any, label: string, isOpen: boolean, onClick?: () => void, active?: boolean, theme?: 'light' | 'dark' }) => (
    <button
        onClick={onClick}
        className={cn(
            "flex items-center gap-3 p-2 rounded-lg transition-colors w-full",
            active
                ? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                : theme === 'dark'
                    ? "hover:bg-slate-800 text-slate-300"
                    : "hover:bg-slate-100 text-slate-700"
        )}
    >
        <Icon size={20} className="shrink-0" />
        {isOpen && <span className="text-sm font-medium whitespace-nowrap overflow-hidden">{label}</span>}
    </button>
);
