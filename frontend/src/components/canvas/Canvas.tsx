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
    CaptureUpdateAction,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import { useCanvas } from '../../hooks/useCanvas';
import { useThemeStore } from '../../stores/useThemeStore';
import { yjsManager } from '../../lib/yjs';
import type { ExcalidrawElement } from '../../lib/yjs';
import { useNavigate } from 'react-router-dom';
import { HistoryPanel } from './HistoryPanel';
import { MobileFAB } from './MobileFAB';
import { AISidebar } from '../ai/AISidebar';
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
    Settings,
    Sun,
    Moon,
    List,
} from 'lucide-react';
import { CollabEventsPanel } from './CollabEventsPanel';

interface CanvasProps {
    roomId?: string;
    roomName?: string;
}

// scrollToNewElements 保留用于将来在浮动模式中使用
// 如果恢复 AIAssistant 请取消注释
/*
const scrollToNewElements = (
    excalidrawAPI: any,
    elementIds: string[],
    allElements: readonly any[]
) => {
    if (!excalidrawAPI || !elementIds?.length || !allElements?.length) return;
    const newElements = allElements.filter(el => elementIds.includes(el.id));
    if (newElements.length === 0) return;
    try {
        excalidrawAPI.scrollToContent(newElements, {
            fitToViewport: true,
            animate: true,
            duration: 300,
        });
        console.log('[Canvas] 已滚动到 AI 创建的元素:', elementIds.length);
    } catch (error) {
        console.warn('[Canvas] scrollToContent 失败:', error);
    }
};
*/

const HISTORY_SIDEBAR_NAME = 'history-panel';
const EVENTS_SIDEBAR_NAME = 'collab-events';

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
    const [showAISidebar, setShowAISidebar] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    // 调试: 鼠标画布坐标
    const [debugCoords, setDebugCoords] = useState<{ x: number; y: number } | null>(null);

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
        console.log('[Canvas] useEffect 触发: excalidrawAPI=', !!excalidrawAPI, 'elements.length=', elements.length);

        if (excalidrawAPI && elements.length > 0) {
            // ========== 调试: updateScene 前的场景状态 ==========
            const beforeElements = excalidrawAPI.getSceneElements();
            console.log('[Canvas] updateScene 前场景元素数量:', beforeElements.length);

            console.log('[Canvas] 调用 updateScene, 传入元素数量:', elements.length);
            // 打印第一个元素的完整数据用于格式验证
            if (elements.length > 0) {
                console.log('[Canvas] 第一个元素完整数据:', JSON.stringify(elements[0], null, 2));
            }

            isRemoteUpdateRef.current = true;

            // 使用 CaptureUpdateAction.NEVER 因为这是远程同步，不需要记录到 undo 历史
            excalidrawAPI.updateScene({
                elements,
                captureUpdate: CaptureUpdateAction.NEVER,
            });

            // ========== 调试: 立即检查 updateScene 结果 ==========
            const afterImmediate = excalidrawAPI.getSceneElements();
            console.log('[Canvas] updateScene 后立即检查:', afterImmediate.length, '个元素');

            if (afterImmediate.length === 0 && elements.length > 0) {
                console.error('[Canvas]   updateScene 未能添加元素! 可能是元素格式问题');
                console.error('[Canvas] 传入的元素类型:', elements.map(e => e.type));
            }

            // 50ms 后再次检查，确认是否被 onChange 覆盖
            setTimeout(() => {
                const afterDelayed = excalidrawAPI.getSceneElements();
                console.log('[Canvas] 50ms 后检查:', afterDelayed.length, '个元素');

                if (afterDelayed.length === 0 && afterImmediate.length > 0) {
                    console.error('[Canvas]   元素被清除了！可能被 onChange 覆盖');
                } else if (afterDelayed.length > 0) {
                    console.log('[Canvas]   场景元素确认存在');
                    // 自动滚动到内容
                    excalidrawAPI.scrollToContent(afterDelayed, {
                        fitToViewport: true,
                        animate: true,
                        duration: 300,
                    });
                }
            }, 50);

            if (files && Object.keys(files).length > 0) {
                excalidrawAPI.addFiles(Object.values(files));
            }

            // 延长保护时间，防止 onChange 覆盖
            setTimeout(() => { isRemoteUpdateRef.current = false; }, 500);
        }
    }, [elements, excalidrawAPI, files]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const onChangeHandler = useCallback((newElements: readonly ExcalidrawElement[], appState: any, newFiles: any) => {
        console.log('[Canvas] onChange 触发, isRemoteUpdate:', isRemoteUpdateRef.current, 'newElements:', newElements.length);

        if (isRemoteUpdateRef.current) {
            console.log('[Canvas] 跳过本地变更 (远程更新保护中)');
            return;
        }
        if (isGuest) return;
        handleChange(newElements, appState, newFiles);
    }, [handleChange, isGuest]);

    const onPointerUpdate = useCallback((payload: { pointer: { x: number; y: number }; button: 'up' | 'down' }) => {
        updatePointer(payload.pointer);
        // 调试: 更新画布坐标显示
        setDebugCoords(payload.pointer);
    }, [updatePointer]);

    const handleBackToRooms = useCallback(() => {
        yjsManager.disconnect();
        navigate('/rooms');
    }, [navigate]);

    const toggleHistorySidebar = useCallback(() => {
        excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
    }, [excalidrawAPI]);

    const toggleEventsSidebar = useCallback(() => {
        excalidrawAPI?.toggleSidebar({ name: EVENTS_SIDEBAR_NAME });
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

            {/* ==================== 调试: 鼠标画布坐标（左下角） ==================== */}
            {debugCoords && (
                <div
                    className={cn(
                        'fixed z-[40] pointer-events-none',
                        'flex items-center gap-2 px-3 py-1.5 rounded-full',
                        'glass-pill',
                        'text-xs font-mono',
                        'transition-all duration-100',
                        isDark ? 'text-green-400' : 'text-green-600'
                    )}
                    style={{
                        left: 'max(12px, env(safe-area-inset-left, 12px))',
                        bottom: 'max(100px, env(safe-area-inset-bottom, 12px))',
                    }}
                >
                    📍 X: {Math.round(debugCoords.x)}, Y: {Math.round(debugCoords.y)}
                </div>
            )}

            {/* ==================== 协作事件侧栏切换按钮（PC） ==================== */}
            {!isMobile && !isGuest && roomId && (
                <button
                    type="button"
                    onClick={toggleEventsSidebar}
                    className={cn(
                        'fixed z-[35] bottom-3 left-1/2 -translate-x-1/2',
                        'bg-white/90 dark:bg-zinc-900/90 shadow-lg border border-zinc-200 dark:border-zinc-800',
                        'rounded-full px-3 py-2 flex items-center gap-2 text-sm font-medium',
                        'text-zinc-700 dark:text-zinc-100',
                        'hover:translate-y-[-1px] hover:shadow-xl transition-all duration-200'
                    )}
                    style={{
                        backdropFilter: 'blur(8px)',
                    }}
                >
                    <List size={16} />
                    <span>协作事件</span>
                </button>
            )}

            {/* ==================== AI 侧边栏 ==================== */}
            {/* 侧边栏自带边缘标签用于展开 */}
            {!isGuest && roomId && !isMobile && (
                <AISidebar
                    roomId={roomId}
                    isDark={isDark}
                    isOpen={showAISidebar}
                    onToggle={() => setShowAISidebar(!showAISidebar)}
                    excalidrawAPI={excalidrawAPI}
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
                        {/* 文件操作区 (Excalidraw 原生) */}
                        <MainMenu.DefaultItems.LoadScene />      {/* 打开 */}
                        <MainMenu.DefaultItems.SaveToActiveFile /> {/* 保存到... */}
                        <MainMenu.DefaultItems.Export />         {/* 导出... (弹窗) */}
                        <MainMenu.DefaultItems.SaveAsImage />    {/* 另存为图片 */}
                        
                        <MainMenu.Separator />

                        {/* 画布操作区 */}
                        <MainMenu.DefaultItems.ClearCanvas />    {/* 重置画布 */}
                        
                        <MainMenu.Separator />

                        {/* 自定义核心功能区 */}
                        <MainMenu.Item 
                            onSelect={() => navigate('/rooms')} 
                            icon={<Home size={16} />}
                        >
                            返回房间列表
                        </MainMenu.Item>

                        {/* 历史版本 (仅在非游客模式且在房间中显示) */}
                        {!isGuest && roomId && (
                            <MainMenu.Item 
                                // 这里假设你代码里定义了 HISTORY_SIDEBAR_NAME 常量，如果没有，请把 name 改为 'history'
                                onSelect={() => excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME })} 
                                icon={<History size={16} />}
                            >
                                历史版本
                            </MainMenu.Item>
                        )}
                        {!isGuest && roomId && (
                            <MainMenu.Item onSelect={toggleEventsSidebar} icon={<List size={16} />}>
                                协作事件
                            </MainMenu.Item>
                        )}
                        {!isGuest && (
                            <MainMenu.Item 
                                onSelect={toggleSettings} 
                                icon={<Settings size={16} />}
                            >
                                模型设置
                            </MainMenu.Item>
                        )}

                        <MainMenu.Separator />

                        {/* 外观设置区 */}

                        {/* 深色模式 (自定义按钮，与全局同步) */}
                        <MainMenu.Item
                            onSelect={() => toggleTheme()}
                            icon={isDark ? <Sun size={16} /> : <Moon size={16} />}
                            shortcut="Shift+Alt+D   "
                        >
                            {isDark ? "浅色模式" : "深色模式"}
                        </MainMenu.Item>

                        {/* 画布背景 */}
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

                {!isGuest && roomId && (
                    <ExcalidrawSidebar name={EVENTS_SIDEBAR_NAME}>
                        <ExcalidrawSidebar.Header>
                            <div className="flex items-center gap-2 px-2">
                                <List size={18} />
                                <span className="font-semibold">协作事件</span>
                            </div>
                        </ExcalidrawSidebar.Header>
                        <div className="h-[calc(100%-50px)] overflow-auto">
                            <CollabEventsPanel />
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
