/**
 * 模块名称：Canvas
 * 主要功能：Excalidraw 画布组件
 * 
 * 集成 Excalidraw 编辑器，支持 PC 端和移动端自适应。
 * 使用 Excalidraw 官方 API 进行自定义扩展。
 */
import React, { useCallback, useEffect, useState, useRef } from 'react';
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
import { ModelSettingsDialog } from '../common/ModelSettingsDialog';
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
    Settings,
} from 'lucide-react';

interface CanvasProps {
    roomId?: string;
    roomName?: string;
}

const HISTORY_SIDEBAR_NAME = 'history-panel';

/**
 * 改进的移动端检测 Hook
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

    const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches;
    const isMobile = minDimension < 768 || (isTouchDevice && width < 1024);
    const isTablet = isTouchDevice && minDimension >= 768 && minDimension < 1024;

    return { isMobile, isTablet, isTouchDevice };
}

export const Canvas: React.FC<CanvasProps> = ({ roomId, roomName }) => {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useThemeStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);
    const isRemoteUpdateRef = useRef(false);
    const { isMobile, isTouchDevice } = useDeviceType();
    const [showAIAssistant, setShowAIAssistant] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

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
        if (isGuest) return;
        handleChange(newElements, appState, newFiles);
    }, [handleChange, isGuest]);

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

    const toggleSettings = useCallback(() => {
        setShowSettings(prev => !prev);
    }, []);

    /**
     * 上传图片到后端并返回文件 ID
     * Excalidraw 会使用此 ID 来引用图片
     */
    const generateIdForFile = useCallback(async (file: File): Promise<string> => {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const token = localStorage.getItem('token');
            const headers: HeadersInit = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch('/api/upload', {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: '上传失败' }));
                throw new Error(error.detail || '上传失败');
            }

            const data = await response.json();
            console.log('[Canvas] 图片上传成功:', data.filename);

            // 返回文件名作为 ID，Excalidraw 会用这个 ID 来引用图片
            return data.filename;
        } catch (error) {
            console.error('[Canvas] 图片上传失败:', error);
            // 失败时返回一个随机 ID，图片将以 base64 形式保存在本地
            return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        }
    }, []);

    const handleClearCanvas = useCallback(() => {
        excalidrawAPI?.resetScene();
    }, [excalidrawAPI]);

    // 使用 Excalidraw 官方 renderTopRightUI 渲染右上角状态
    // 移动端不显示，由 MobileFAB 统一处理状态显示
    const renderTopRightUI = useCallback(() => {
        // 移动端不显示，避免遮挡工具栏
        if (isMobile) return null;

        const StatusIcon = !isConnected ? WifiOff : (!isSynced ? Loader2 : Wifi);
        const statusText = !isConnected ? '离线' : (!isSynced ? '同步中' : '已连接');
        const statusBg = !isConnected
            ? 'linear-gradient(135deg, #ef4444 0%, #f43f5e 100%)'
            : (!isSynced
                ? 'linear-gradient(135deg, #f59e0b 0%, #f97316 100%)'
                : 'linear-gradient(135deg, #10b981 0%, #14b8a6 100%)');

        return (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {/* 在线人数 */}
                {collaborators.size > 0 && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '999px',
                        background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: 500,
                        boxShadow: '0 4px 12px rgba(139, 92, 246, 0.3)',
                    }}>
                        <Users size={13} strokeWidth={2.5} />
                        <span>{collaborators.size + 1}</span>
                    </div>
                )}

                {/* 连接状态 */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '999px',
                    background: statusBg,
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 500,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}>
                    <StatusIcon
                        size={13}
                        strokeWidth={2.5}
                        style={!isSynced && isConnected ? { animation: 'spin 1s linear infinite' } : undefined}
                    />
                    <span>{statusText}</span>
                </div>
            </div>
        );
    }, [isConnected, isSynced, collaborators.size, isMobile]);

    return (
        <div className="canvas-container">
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
                        bottom: 'max(60px, env(safe-area-inset-bottom, 12px))',
                    }}
                >
                    <Sparkles size={12} className={isDark ? 'text-violet-400' : 'text-violet-500'} />
                    <span className="truncate max-w-[150px]">{roomName || `房间 ${roomId?.slice(0, 8)}`}</span>
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
                        zenModeEnabled: false,
                        gridModeEnabled: false,
                    },
                }}
                onChange={onChangeHandler}
                onPointerUpdate={isTouchDevice ? undefined : onPointerUpdate}
                theme={isDark ? 'dark' : 'light'}
                langCode="zh-CN"
                viewModeEnabled={false}
                zenModeEnabled={false}
                gridModeEnabled={false}
                renderTopRightUI={renderTopRightUI}
                generateIdForFile={generateIdForFile}
                UIOptions={{
                    canvasActions: {
                        loadScene: !isGuest,
                        export: { saveFileToDisk: !isGuest },
                        saveToActiveFile: !isGuest,
                        clearCanvas: !isGuest,
                        changeViewBackgroundColor: !isGuest,
                        toggleTheme: true,
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
                        {!isGuest && (
                            <MainMenu.Item onSelect={toggleSettings} icon={<Settings size={16} />}>
                                模型设置
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

            {/* 模型设置浮动弹窗 */}
            <ModelSettingsDialog
                open={showSettings}
                onClose={() => setShowSettings(false)}
                isDark={isDark}
            />
        </div>
    );
};
