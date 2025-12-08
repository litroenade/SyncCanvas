import React, { useState } from 'react';
import { Settings, ChevronLeft, ChevronRight, Download, Undo, Redo, Sun, Moon, Home, History } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { yjsManager } from '../../lib/yjs';
import { useThemeStore } from '../../stores/useThemeStore';
import { SettingsModal } from '../common/SettingsModal';
import { HistoryPanel } from './HistoryPanel';

const undo = () => {
    yjsManager.undoManager?.undo();
};

const redo = () => {
    yjsManager.undoManager?.redo();
};

const leaveRoom = () => {
    yjsManager.disconnect();
};

interface SidebarProps {
    roomId?: string;
    onExport?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ roomId, onExport }) => {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);
    const [activePanel, setActivePanel] = useState<'history' | 'none'>('none');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { theme, toggleTheme } = useThemeStore();

    // 假设 Excalidraw 组件会处理返回逻辑，这里只需处理 sidebar 自身
    const handleBackToRooms = () => {
        leaveRoom();
        navigate('/rooms');
    };

    const togglePanel = (panel: 'history') => {
        if (activePanel === panel) {
            setActivePanel('none');
        } else {
            setActivePanel(panel);
            setIsOpen(true);
        }
    };

    // 检查是否为游客
    const isGuest = localStorage.getItem('isGuest') === 'true' && !localStorage.getItem('token');

    return (
        <>
            <div
                className={cn(
                    "fixed top-48 left-0 h-[calc(100%-48px)] transition-all duration-300 z-40 flex flex-col pointer-events-none", // pointer-events-none 让出点击
                    // 这里不设置背景，让 Sidebar Item 浮动，或者设置背景
                    // 既然是 Overlay，我们希望它看起来像浮在上面的工具栏，或者一个抽屉
                )}
            >
                {/* 实际的 Sidebar 容器，恢复 pointer-events */}
                <div className={cn(
                    "h-full shadow-sm border-r pointer-events-auto transition-all duration-300 flex flex-col",
                    isOpen ? "w-64" : "w-12",
                    theme === 'dark' ? "bg-slate-900 border-slate-700" : "bg-white border-slate-200"
                )}>
                    {/* Toggle Button */}
                    <button
                        onClick={() => setIsOpen(!isOpen)}
                        title={isOpen ? '收起侧边栏' : '展开侧边栏'}
                        className={cn(
                            "absolute -right-3 top-6 border rounded-full p-1 shadow-sm transition-colors",
                            theme === 'dark'
                                ? "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                                : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                        )}
                    >
                        {isOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
                    </button>

                    <div className="flex-1 overflow-y-auto py-4">
                        <div className="flex flex-col gap-1 px-2">
                            <SidebarItem
                                icon={Home}
                                label="返回房间列表"
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

                                    <SidebarItem
                                        icon={History}
                                        label="历史版本"
                                        isOpen={isOpen}
                                        onClick={() => togglePanel('history')}
                                        active={activePanel === 'history'}
                                        theme={theme}
                                    />

                                    {activePanel === 'history' && isOpen && roomId && (
                                        <div className={cn(
                                            "mt-2 mb-2 border-t border-b py-2 flex-1 overflow-hidden", // flex-1 to fill space
                                            theme === 'dark' ? "border-slate-700" : "border-slate-100"
                                        )} style={{ minHeight: '300px' }}>
                                            <HistoryPanel roomId={roomId} />
                                        </div>
                                    )}

                                    <div className={cn("h-px my-2 mx-2", theme === 'dark' ? "bg-slate-700" : "bg-slate-100")} />
                                </>
                            )}

                            <SidebarItem
                                icon={theme === 'dark' ? Moon : Sun}
                                label={theme === 'dark' ? "暗色模式" : "亮色模式"}
                                isOpen={isOpen}
                                onClick={toggleTheme}
                                theme={theme}
                            />

                            <SidebarItem icon={Settings} label="设置" isOpen={isOpen} onClick={() => setIsSettingsOpen(true)} theme={theme} />
                            {onExport && <SidebarItem icon={Download} label="导出" isOpen={isOpen} onClick={onExport} theme={theme} />}
                        </div>
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
        title={label}
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
