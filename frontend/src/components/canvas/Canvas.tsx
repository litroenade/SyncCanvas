/**
 * 模块名称：Canvas
 * 主要功能：Excalidraw 画布组件
 * 
 * 集成 Excalidraw 编辑器，支持 PC 端和移动端自适应。
 */
import React, { useCallback, useEffect, useState, useRef, useMemo } from 'react';
import {
    Excalidraw,
    MainMenu,
    Sidebar as ExcalidrawSidebar,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import { useCanvas } from '../../hooks/useCanvas';
import { useThemeStore } from '../../stores/useThemeStore';
import { yjsManager } from '../../lib/yjs';
import type { ExcalidrawElement } from '../../lib/yjs';
import { useNavigate } from 'react-router-dom';
import { HistoryPanel } from './HistoryPanel';
import { MobileFAB } from './MobileFAB';
import { AIAssistant } from './AIAssistant';
import { cn } from '../../lib/utils';
import {
    Home,
    History,
    Users,
    Wifi,
    WifiOff,
    Loader2,
    Sparkles,
    Bot,
} from 'lucide-react';

interface CanvasProps {
    roomId?: string;
}

const HISTORY_SIDEBAR_NAME = 'history-panel';

/**
 * 改进的移动端检测 Hook
 * 使用多重判断：屏幕宽度 + 触摸能力 + 指针类型
 */
const useDeviceType = () => {
    const [deviceInfo, setDeviceInfo] = useState(() => {
        if (typeof window === 'undefined') {
            return { isMobile: false, isTablet: false, isTouchDevice: false };
        }
        return getDeviceInfo();
    });

    useEffect(() => {
        const handleResize = () => {
            setDeviceInfo(getDeviceInfo());
        };
        
        window.addEventListener('resize', handleResize);
        window.addEventListener('orientationchange', handleResize);
        
        return () => {
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('orientationchange', handleResize);
        };
    }, []);

    return deviceInfo;
};

function getDeviceInfo() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const minDimension = Math.min(width, height);
    
    // 使用 CSS 媒体查询检测触摸设备
    const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches;
    
    // 小屏幕手机 (宽度 < 768px 或者触摸设备且宽度 < 1024px)
    const isMobile = minDimension < 768 || (isTouchDevice && width < 1024);
    
    // 平板 (768px - 1024px 且是触摸设备)
    const isTablet = isTouchDevice && minDimension >= 768 && minDimension < 1024;
    
    return { isMobile, isTablet, isTouchDevice };
}

/**
 * 连接状态配置
 */
const getStatusConfig = (isConnected: boolean, isSynced: boolean) => {
    if (!isConnected) {
        return {
            color: 'text-red-400',
            bgGradient: 'from-red-500/90 to-rose-500/90',
            dotColor: 'bg-red-400',
            icon: WifiOff,
            text: '离线',
            animate: false,
        };
    }
    if (!isSynced) {
        return {
            color: 'text-amber-400',
            bgGradient: 'from-amber-500/90 to-orange-500/90',
            dotColor: 'bg-amber-400',
            icon: Loader2,
            text: '同步中',
            animate: true,
        };
    }
    return {
        color: 'text-emerald-400',
        bgGradient: 'from-emerald-500/90 to-teal-500/90',
        dotColor: 'bg-emerald-400',
        icon: Wifi,
        text: '已连接',
        animate: false,
    };
};

export const Canvas: React.FC<CanvasProps> = ({ roomId }) => {
    const navigate = useNavigate();
    const { theme, excalidrawConfig, setExcalidrawConfig, toggleTheme } = useThemeStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);
    const isRemoteUpdateRef = useRef(false);
    const { isMobile, isTouchDevice } = useDeviceType();
    const [showAIAssistant, setShowAIAssistant] = useState(false);

    const {
        elements,
        files,
        collaborators,
        isConnected,
        isSynced,
        handleChange,
        updatePointer,
        undo,
        redo,
    } = useCanvas(roomId);

    const isDark = theme === 'dark';
    const isGuest = localStorage.getItem('isGuest') === 'true' && !localStorage.getItem('token');

    // 状态配置
    const statusConfig = useMemo(
        () => getStatusConfig(isConnected, isSynced),
        [isConnected, isSynced]
    );
    const StatusIcon = statusConfig.icon;

    // 同步远程元素更新
    useEffect(() => {
        if (excalidrawAPI && elements.length > 0) {
            isRemoteUpdateRef.current = true;
            excalidrawAPI.updateScene({ elements });
            if (files && Object.keys(files).length > 0) {
                excalidrawAPI.addFiles(Object.values(files));
            }
            setTimeout(() => { isRemoteUpdateRef.current = false; }, 100);
        }
    }, [elements, excalidrawAPI, files]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const onChangeHandler = useCallback((newElements: readonly ExcalidrawElement[], appState: any, newFiles: any) => {
        if (isRemoteUpdateRef.current) return;
        // 游客模式不同步更改到服务器
        if (isGuest) return;
        if (appState.viewBackgroundColor !== excalidrawConfig.viewBackgroundColor) {
            setTimeout(() => setExcalidrawConfig({ viewBackgroundColor: appState.viewBackgroundColor }), 500);
        }
        handleChange(newElements, appState, newFiles);
    }, [handleChange, excalidrawConfig.viewBackgroundColor, setExcalidrawConfig, isGuest]);

    const onPointerUpdate = useCallback((payload: { pointer: { x: number; y: number }; button: 'up' | 'down' }) => {
        updatePointer(payload.pointer);
    }, [updatePointer]);

    const handleBackToRooms = useCallback(() => {
        yjsManager.disconnect();
        navigate('/rooms');
    }, [navigate]);

    const toggleHistorySidebar = useCallback(() => {
        excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
    }, [excalidrawAPI]);

    const handleClearCanvas = useCallback(() => {
        excalidrawAPI?.resetScene();
    }, [excalidrawAPI]);

    return (
        <div className="canvas-container">
            {/* ==================== PC 端状态栏 ==================== */}
            {!isMobile && (
                <div className="fixed z-[40] flex items-center gap-2 pointer-events-none"
                     style={{
                         top: 'max(12px, env(safe-area-inset-top, 12px))',
                         right: 'max(12px, env(safe-area-inset-right, 12px))',
                     }}>
                    {/* 在线人数 */}
                    {collaborators.size > 0 && (
                        <div className={cn(
                            'pointer-events-auto',
                            'flex items-center gap-1.5 px-3 py-1.5 rounded-full',
                            'bg-gradient-to-r from-violet-500/90 to-purple-500/90',
                            'text-white text-xs font-medium',
                            'shadow-lg shadow-violet-500/20',
                            'backdrop-blur-sm',
                            'transition-all duration-300 ease-out',
                            'hover:shadow-violet-500/30 hover:scale-[1.02]'
                        )}>
                            <Users size={13} strokeWidth={2.5} />
                            <span>{collaborators.size + 1}</span>
                        </div>
                    )}
                    
                    {/* 连接状态 */}
                    <div className={cn(
                        'pointer-events-auto relative',
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-full',
                        'bg-gradient-to-r',
                        statusConfig.bgGradient,
                        'text-white text-xs font-medium',
                        'shadow-lg backdrop-blur-sm',
                        'transition-all duration-300 ease-out'
                    )}>
                        <StatusIcon 
                            size={13} 
                            strokeWidth={2.5}
                            className={statusConfig.animate ? 'animate-spin' : ''} 
                        />
                        <span>{statusConfig.text}</span>
                    </div>
                </div>
            )}

            {/* ==================== 移动端 FAB 菜单 ==================== */}
            {isMobile && (
                <MobileFAB
                    isDark={isDark}
                    isConnected={isConnected}
                    isSynced={isSynced}
                    collaboratorsCount={collaborators.size}
                    onUndo={undo}
                    onRedo={redo}
                    onToggleTheme={toggleTheme}
                    onToggleHistory={toggleHistorySidebar}
                    onClearCanvas={handleClearCanvas}
                    onBackToRooms={handleBackToRooms}
                />
            )}

            {/* ==================== PC 端房间信息（左下角） ==================== */}
            {!isMobile && roomId && (
                <div 
                    className={cn(
                        'canvas-room-info',
                        'fixed z-[40] pointer-events-none',
                        'flex items-center gap-2 px-3 py-1.5 rounded-full',
                        'glass-pill',
                        'text-xs font-medium',
                        'transition-all duration-300',
                        isDark ? 'text-zinc-400' : 'text-zinc-500'
                    )}
                    style={{
                        left: 'max(12px, env(safe-area-inset-left, 12px))',
                        bottom: 'max(12px, env(safe-area-inset-bottom, 12px))',
                    }}
                >
                    <Sparkles size={12} className={isDark ? 'text-violet-400' : 'text-violet-500'} />
                    <span className="opacity-60">房间</span>
                    <span className="font-mono">{roomId.slice(0, 8)}</span>
                </div>
            )}

            {/* ==================== AI 助手按钮（右下角） ==================== */}
            {!isGuest && roomId && !isMobile && (
                <button
                    onClick={() => setShowAIAssistant(!showAIAssistant)}
                    className={cn(
                        'fixed z-[45] p-3 rounded-2xl',
                        'transition-all duration-300',
                        'shadow-lg hover:shadow-xl',
                        'active:scale-95',
                        showAIAssistant
                            ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white'
                            : isDark
                                ? 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                                : 'bg-white hover:bg-zinc-50 text-zinc-700 border border-zinc-200'
                    )}
                    style={{
                        right: 'max(16px, env(safe-area-inset-right, 16px))',
                        bottom: 'max(16px, env(safe-area-inset-bottom, 16px))',
                    }}
                    title="AI 助手"
                >
                    <Bot size={22} />
                </button>
            )}

            {/* ==================== AI 助手面板 ==================== */}
            {!isGuest && roomId && (
                <AIAssistant
                    roomId={roomId}
                    isDark={isDark}
                    isOpen={showAIAssistant}
                    onClose={() => setShowAIAssistant(false)}
                />
            )}

            {/* ==================== Excalidraw 画布 ==================== */}
            <Excalidraw
                excalidrawAPI={(api) => setExcalidrawAPI(api)}
                initialData={{
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    elements: [] as any,
                    appState: {
                        theme: isDark ? 'dark' : 'light',
                        viewBackgroundColor: excalidrawConfig?.viewBackgroundColor || (isDark ? '#121212' : '#ffffff'),
                        zenModeEnabled: false,
                        gridModeEnabled: false,
                    },
                }}
                onChange={onChangeHandler}
                onPointerUpdate={isTouchDevice ? undefined : onPointerUpdate}
                theme={isDark ? 'dark' : 'light'}
                langCode="zh-CN"
                // 游客不使用 viewMode，允许使用激光笔
                viewModeEnabled={false}
                zenModeEnabled={false}
                gridModeEnabled={false}
                UIOptions={{
                    canvasActions: {
                        loadScene: !isGuest,
                        export: { saveFileToDisk: !isGuest },
                        saveToActiveFile: !isGuest,
                        clearCanvas: !isGuest,
                        changeViewBackgroundColor: !isGuest,
                        toggleTheme: !isMobile,
                    },
                    welcomeScreen: false,
                }}
            >
                {/* PC 端主菜单 */}
                {!isMobile && (
                    <MainMenu>
                        <MainMenu.DefaultItems.LoadScene />
                        <MainMenu.DefaultItems.SaveToActiveFile />
                        <MainMenu.DefaultItems.Export />
                        <MainMenu.DefaultItems.SaveAsImage />
                        <MainMenu.Separator />
                        <MainMenu.DefaultItems.ClearCanvas />
                        <MainMenu.Separator />
                        <MainMenu.Item onSelect={handleBackToRooms} icon={<Home size={16} />}>
                            返回房间列表
                        </MainMenu.Item>
                        {!isGuest && roomId && (
                            <MainMenu.Item onSelect={toggleHistorySidebar} icon={<History size={16} />}>
                                历史版本
                            </MainMenu.Item>
                        )}
                        <MainMenu.Separator />
                        <MainMenu.DefaultItems.ToggleTheme />
                        <MainMenu.DefaultItems.ChangeCanvasBackground />
                    </MainMenu>
                )}

                {/* 历史版本侧边栏 */}
                {!isGuest && roomId && (
                    <ExcalidrawSidebar name={HISTORY_SIDEBAR_NAME}>
                        <ExcalidrawSidebar.Header>
                            <div className="flex items-center gap-2 px-2">
                                <History size={18} />
                                <span className="font-semibold">历史版本</span>
                            </div>
                        </ExcalidrawSidebar.Header>
                        <div className="h-[calc(100%-50px)] overflow-auto p-2">
                            <HistoryPanel roomId={roomId} />
                        </div>
                    </ExcalidrawSidebar>
                )}
            </Excalidraw>
        </div>
    );
};
