/**
 * 模块名称：Canvas
 * 主要功能：Excalidraw 画布组件
 * 
 * 集成 Excalidraw 编辑器，通过 Yjs 实现实时协作。
 */
import React, { useCallback, useEffect, useState, useRef } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
// 必须导入 Excalidraw 的核心 CSS，否则图标会显示异常
import '@excalidraw/excalidraw/index.css';
import { useCanvas } from '../../hooks/useCanvas';
import { useThemeStore } from '../../stores/useThemeStore';
import type { ExcalidrawElement } from '../../lib/yjs';
import { Sidebar } from './Sidebar';

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
    const { theme, excalidrawConfig, setExcalidrawConfig } = useThemeStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);
    const isRemoteUpdateRef = useRef(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const {
        elements,
        files,
        collaborators,
        isConnected,
        isSynced,
        handleChange,
        updatePointer,
    } = useCanvas(roomId);


    // 当远程元素变化时，更新 Excalidraw
    useEffect(() => {
        if (excalidrawAPI && elements.length > 0) {
            isRemoteUpdateRef.current = true;
            isRemoteUpdateRef.current = true;
            excalidrawAPI.updateScene({
                elements: elements,
                // Files should be passed to updateScene if available
                // Excalidraw will merge them
            });
            if (files && Object.keys(files).length > 0) {
                excalidrawAPI.addFiles(Object.values(files));
            }
            setTimeout(() => {
                isRemoteUpdateRef.current = false;
            }, 100);
        }
    }, [elements, excalidrawAPI]);

    // 处理本地变更
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const onChangeHandler = useCallback((newElements: readonly ExcalidrawElement[], appState: any, files: any) => {
        if (isRemoteUpdateRef.current) return;

        // 持久化背景颜色
        if (appState.viewBackgroundColor !== excalidrawConfig.viewBackgroundColor) {
            // 使用 debounce 避免频繁更新 store
            setTimeout(() => {
                setExcalidrawConfig({ viewBackgroundColor: appState.viewBackgroundColor });
            }, 500);
        }

        handleChange(newElements, appState, files);
    }, [handleChange, excalidrawConfig.viewBackgroundColor, setExcalidrawConfig]);

    // 处理指针移动
    const onPointerUpdate = useCallback((payload: {
        pointer: { x: number; y: number };
        button: 'up' | 'down';
    }) => {
        updatePointer(payload.pointer);
    }, [updatePointer]);



    // 检查是否为游客模式
    const isGuest = localStorage.getItem('isGuest') === 'true' && !localStorage.getItem('token');

    // 根据主题设置顶部栏样式
    const isDark = theme === 'dark';

    // 自定义网格样式 (覆盖原生网格)
    useEffect(() => {
        const style = document.createElement('style');
        style.innerHTML = `
            .excalidraw .excalidraw-container {
                ${isDark
                ? 'background-image: radial-gradient(#374151 1px, transparent 1px);'
                : 'background-image: radial-gradient(#e5e7eb 1px, transparent 1px);'
            }
                background-size: 20px 20px;
            }
        `;
        document.head.appendChild(style);
        return () => {
            document.head.removeChild(style);
        };
    }, [isDark]);

    const renderTopRightUI = useCallback(() => {
        return (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {/* 协作者状态 */}
                {collaborators.size > 0 && (
                    <div style={{
                        padding: '4px 8px',
                        backgroundColor: '#dbeafe',
                        color: '#1d4ed8',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 500,
                    }}>
                        {collaborators.size} 人在线
                    </div>
                )}

                {/* 连接状态 */}
                <div style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                    backgroundColor: isConnected
                        ? (isSynced ? '#dcfce7' : '#fef9c3')
                        : '#fee2e2',
                    color: isConnected
                        ? (isSynced ? '#15803d' : '#a16207')
                        : '#dc2626',
                }}>
                    {isConnected ? (isSynced ? '已同步' : '同步中') : '连接中'}
                </div>

            </div>
        );
    }, [isDark, isConnected, isSynced, collaborators.size]);

    return (
        <div className="excalidraw-wrapper">
            {/* Excalidraw 编辑器容器 */}
            <div
                ref={containerRef}
                className="excalidraw-editor-container"
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                }}
            >
                <Excalidraw
                    excalidrawAPI={(api) => setExcalidrawAPI(api)}
                    initialData={{
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        elements: [] as any,
                        appState: {
                            theme: isDark ? 'dark' : 'light',
                            viewBackgroundColor: excalidrawConfig?.viewBackgroundColor || (isDark ? '#121212' : '#ffffff'),
                            zenModeEnabled: false,
                            gridModeEnabled: false, // 禁用原生网格，使用 CSS 自定义
                        },
                    }}
                    onChange={onChangeHandler}
                    onPointerUpdate={onPointerUpdate}
                    theme={isDark ? 'dark' : 'light'}
                    langCode="zh-CN"
                    viewModeEnabled={isGuest}
                    zenModeEnabled={false}
                    gridModeEnabled={false}
                    renderTopRightUI={renderTopRightUI}
                    UIOptions={{
                        canvasActions: {
                            loadScene: !isGuest,
                            export: { saveFileToDisk: true },
                            saveToActiveFile: !isGuest,
                            clearCanvas: !isGuest,
                            changeViewBackgroundColor: true,
                        },
                        welcomeScreen: false,
                    }}
                />
            </div>

            {/* 侧边栏 */}
            <Sidebar
                roomId={roomId}
                onExport={excalidrawAPI ? () => {
                    // Excalidraw 的导出由内部 UI 处理
                } : undefined}
            />
        </div>
    );
};
