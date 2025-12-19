/**
 * Canvas.tsx
 * 适配 @excalidraw/excalidraw@0.18.x
 * 支持：选中形状 / 线条 → 自动弹出对应 Palette
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

import { ShapePalette } from './ShapePalette';
import { LinePalette } from './LinePalette';
import { HistoryPanel } from './HistoryPanel';
import { ModelSettingsDialog } from '../common/ModelSettingsDialog';

import {
  Home,
  History,
  Settings,
} from 'lucide-react';

interface CanvasProps {
  roomId?: string;
  roomName?: string;
}

const HISTORY_SIDEBAR_NAME = 'history-panel';

export const Canvas: React.FC<CanvasProps> = ({ roomId }) => {
  const navigate = useNavigate();
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

  /** ⚠️ 0.18.x 必须用 any */
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);

  /** ⭐ 当前应显示的面板 */
  const [selectedPanel, setSelectedPanel] = useState<'shape' | 'line' | null>(null);

  const isRemoteUpdateRef = useRef(false);

  const {
    elements,
    files,
    isConnected,
    isSynced,
    handleChange,
  } = useCanvas(roomId);

  const isGuest =
    localStorage.getItem('isGuest') === 'true' &&
    !localStorage.getItem('token');

  /** ================== 同步远端元素 ================== */
  useEffect(() => {
    if (!excalidrawAPI) return;
    if (elements.length === 0) return;

    isRemoteUpdateRef.current = true;
    excalidrawAPI.updateScene({ elements });

    if (files && Object.keys(files).length > 0) {
      excalidrawAPI.addFiles(Object.values(files));
    }

    setTimeout(() => {
      isRemoteUpdateRef.current = false;
    }, 100);
  }, [elements, files, excalidrawAPI]);

  /** ================== ⭐ 关键：选中监听 ================== */
  const onChangeHandler = useCallback(
    (
      newElements: readonly ExcalidrawElement[],
      appState: any,
      newFiles: any,
    ) => {
      if (!isRemoteUpdateRef.current && !isGuest) {
        handleChange(newElements, appState, newFiles);
      }

      const selectedIds = Object.keys(appState.selectedElementIds || {});

      /** 空白 or 多选 → 隐藏面板 */
      if (selectedIds.length !== 1) {
        setSelectedPanel(null);
        return;
      }

      const el = newElements.find(e => e.id === selectedIds[0]);
      if (!el) {
        setSelectedPanel(null);
        return;
      }

      /** 判断类型 */
      if (
        el.type === 'rectangle' ||
        el.type === 'ellipse' ||
        el.type === 'diamond' ||
        el.type === 'triangle' ||
        el.type === 'hexagon' ||
        el.type === 'star'
      ) {
        setSelectedPanel('shape');
      } else if (el.type === 'line' || el.type === 'arrow') {
        setSelectedPanel('line');
      } else {
        setSelectedPanel(null);
      }
    },
    [handleChange, isGuest],
  );

  /** ================== UI 操作 ================== */
  const handleBackToRooms = useCallback(() => {
    yjsManager.disconnect();
    navigate('/rooms');
  }, [navigate]);

  const toggleHistorySidebar = useCallback(() => {
    excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
  }, [excalidrawAPI]);

  /** ================== 渲染 ================== */
  return (
    <div className="canvas-container">
      <Excalidraw
        excalidrawAPI={(api) => setExcalidrawAPI(api)}
        onChange={onChangeHandler}
        theme={isDark ? 'dark' : 'light'}
        viewModeEnabled={false}
        zenModeEnabled={false}
        gridModeEnabled={false}
        UIOptions={{
          welcomeScreen: false,
        }}
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

          <MainMenu.Item icon={<Settings size={16} />}>
            设置
          </MainMenu.Item>
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

            {/* ⚠️ HistoryPanel 要求 roomId: string */}
            <HistoryPanel roomId={roomId} />
          </ExcalidrawSidebar>
        )}
      </Excalidraw>

      {/* ⭐ Shape 面板 */}
      {selectedPanel === 'shape' && (
        <ShapePalette
          excalidrawAPI={excalidrawAPI}
          isDark={isDark}
        />
      )}

      {/* ⭐ Line 面板 */}
      {selectedPanel === 'line' && (
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

      {/* 模型设置弹窗（保持 props 完整，避免 TS 报错） */}
      <ModelSettingsDialog
        open={false}
        onClose={() => {}}
        isDark={isDark}
      />
    </div>
  );
};
