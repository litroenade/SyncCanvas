/**
 * Canvas.tsx — draw.io 模式
 * 行为：先选工具 → 出 Palette → 再在画布拖动创建
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Excalidraw,
  MainMenu,
  Sidebar as ExcalidrawSidebar,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

import { useNavigate } from 'react-router-dom';
import type { ExcalidrawElement } from '../../lib/yjs';
import { yjsManager } from '../../lib/yjs';

import { useCanvas } from '../../hooks/useCanvas';
import { useThemeStore } from '../../stores/useThemeStore';

import ShapePalette from './ShapePalette';
import LinePalette from './LinePalette';

import { HistoryPanel } from './HistoryPanel';
import { ModelSettingsDialog } from '../common/ModelSettingsDialog';

import { Home, History } from 'lucide-react';

interface CanvasProps {
  roomId?: string;
  roomName?: string;
}

type ToolPanelMode = 'shape' | 'line' | null;

const HISTORY_SIDEBAR_NAME = 'history-panel';

export const Canvas: React.FC<CanvasProps> = ({ roomId }) => {
  const navigate = useNavigate();
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

  /** Excalidraw API（0.18.x 用 any） */
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);

  /** 当前显示的 Palette（draw.io 核心） */
  const [toolPanelMode, setToolPanelMode] =
    useState<ToolPanelMode>(null);
  const lastToolTypeRef = useRef<string | null>(null);

  const isRemoteUpdateRef = useRef(false);

  const {
    elements,
    files,
    handleChange,
  } = useCanvas(roomId);

  const isGuest =
    localStorage.getItem('isGuest') === 'true' &&
    !localStorage.getItem('token');

  /* ================= 远端同步 ================= */
  useEffect(() => {
    if (!excalidrawAPI) return;

    isRemoteUpdateRef.current = true;
    excalidrawAPI.updateScene({ elements });

    if (files && Object.keys(files).length > 0) {
      excalidrawAPI.addFiles(Object.values(files));
    }

    setTimeout(() => {
      isRemoteUpdateRef.current = false;
    }, 100);
  }, [elements, files, excalidrawAPI]);

  /* ================= 核心：监听工具切换 ================= */
  const updateToolPanel = useCallback(
    (activeTool?: string | null) => {
      if (activeTool === lastToolTypeRef.current) return;

      lastToolTypeRef.current = activeTool ?? null;

      if (
        activeTool === 'rectangle' ||
        activeTool === 'ellipse' ||
        activeTool === 'diamond' ||
        activeTool === 'triangle' ||
        activeTool === 'hexagon' ||
        activeTool === 'star'
      ) {
        setToolPanelMode('shape');
        return;
      }

      if (activeTool === 'line' || activeTool === 'arrow') {
        setToolPanelMode('line');
        return;
      }

      if (activeTool === 'selection') {
        setToolPanelMode(null);
      }
    },
    [],
  );

  const onChangeHandler = useCallback(
    (
      newElements: readonly ExcalidrawElement[],
      appState: any,
      newFiles: any,
    ) => {
      if (!isRemoteUpdateRef.current && !isGuest) {
        handleChange(newElements, appState, newFiles);
      }

      updateToolPanel(appState.activeTool?.type);
    },
    [handleChange, isGuest, updateToolPanel],
  );

  /* ================= UI ================= */
  const handleBackToRooms = useCallback(() => {
    yjsManager.disconnect();
    navigate('/rooms');
  }, [navigate]);

  const toggleHistorySidebar = useCallback(() => {
    excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
  }, [excalidrawAPI]);

  /**
   * 有些版本的 Excalidraw 不会在仅切换工具时触发 onChange，
   * 这里轮询 activeTool，确保点击矩形/线条后立即弹出 Palette。
   */
  useEffect(() => {
    if (!excalidrawAPI) return;

    const intervalId = window.setInterval(() => {
      const activeTool = excalidrawAPI.getAppState?.()?.activeTool?.type;
      updateToolPanel(activeTool);
    }, 150);

    return () => window.clearInterval(intervalId);
  }, [excalidrawAPI, updateToolPanel]);

  return (
    <div className="canvas-container">
      <Excalidraw
        excalidrawAPI={(api) => setExcalidrawAPI(api)}
        onChange={onChangeHandler}
        theme={isDark ? 'dark' : 'light'}
        viewModeEnabled={false}
        zenModeEnabled={false}
        gridModeEnabled={false}
        UIOptions={{ welcomeScreen: false }}
      >
        {/* 主菜单 */}
        <MainMenu>
          <MainMenu.Item
            onSelect={handleBackToRooms}
            icon={<Home size={16} />}
          >
            返回房间列表
          </MainMenu.Item>

          {roomId && (
            <MainMenu.Item
              onSelect={toggleHistorySidebar}
              icon={<History size={16} />}
            >
              历史版本
            </MainMenu.Item>
          )}
        </MainMenu>

        {/* 历史侧边栏 */}
        {roomId && (
          <ExcalidrawSidebar name={HISTORY_SIDEBAR_NAME}>
            <ExcalidrawSidebar.Header>
              <div className="flex items-center gap-2 px-2">
                <History size={18} />
                <span className="font-semibold">历史版本</span>
              </div>
            </ExcalidrawSidebar.Header>
            <HistoryPanel roomId={roomId} />
          </ExcalidrawSidebar>
        )}
      </Excalidraw>

      {/* ================= draw.io 风格 Palette ================= */}

      {toolPanelMode === 'shape' && (
        <ShapePalette
          excalidrawAPI={excalidrawAPI}
          isDark={isDark}
        />
      )}

      {toolPanelMode === 'line' && (
        <LinePalette
          excalidrawAPI={excalidrawAPI}
          isDark={isDark}
          lineTypes={[
            'straight',
            'dashed',
            'arrow',
            'doubleArrow',
            'dotLine',
            'arrowDashed',
            'curved',
            'curvedArrow',
            'angled',
            'angledArrow',
          ]}
        />
      )}

      {/* 防止 TS 报错 */}
      <ModelSettingsDialog
        open={false}
        onClose={() => {}}
        isDark={isDark}
      />
    </div>
  );
};
