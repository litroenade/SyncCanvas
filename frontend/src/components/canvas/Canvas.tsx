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
import { AIAssistant } from './AIAssistant';
import { MobileFAB } from './MobileFAB';
import { SettingsPanel } from './SettingsPanel';

import { HistoryPanel } from './HistoryPanel';
import { ModelSettingsDialog } from '../common/ModelSettingsDialog';

import { Home, History, Boxes, Bot, Settings } from 'lucide-react';

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

  const [umlLibraryItems, setUmlLibraryItems] = useState<any[]>([]);

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

  const [umlNameMap, setUmlNameMap] = useState<Record<string, string>>({});

  // AI 助手状态
  const [isAIOpen, setIsAIOpen] = useState(false);

  // 设置面板状态
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // 检测移动端
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 硬编码名称映射，按过滤后的可见顺序（已排除 1,3,13,14,15,20）
  const hardcodedNameMap: Record<string, string> = {
    "0": "类图矩形",              // 原索引 0: 带分隔线的矩形（类/实体/用例）
    "1": "简单矩形",              // 原索引 2: 基础矩形框
    "2": "导航关联",              // 原索引 4: 空心菱形箭头
    "3": "聚合关系", 
    "4": "组合关系",  
    "5": "泛化关系",         // 原索引 7: 空心三角箭头
    "6": "可见性修饰符+",              // 原索引 8: 两端带圆圈的线
    "7": "基数标注 n..m",              // 原索引 9: 单端圆圈的线
    "8": "基数标注 0..n",              // 原索引 10: 虚线箭头
    "9": "基数标注 1",              // 原索引 11: 实线箭头
    "10": "基数标注 0..1",        // 原索引 12: 文本标注
    "11": "扩展点",        // 原索引 16: 文本标注
    "12": "参与者",        // 原索引 17: 文本标注
    "13": "控制流、对象流、消息流",             // 原索引 18: ER图实体
    "14": "接口",           // 原索引 19: 用例图参与者
  };

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
        activeTool === 'star' ||
        activeTool === 'line' ||
        activeTool === 'arrow'
      ) {
        setToolPanelMode('shape');
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

  const handleImportUmlLibrary = useCallback(async () => {
    if (!excalidrawAPI) return;

    try {
      const base = import.meta.env.BASE_URL ?? '/';

      // 优先使用硬编码映射，避免文件加载缓存问题
      let nameMapLocal: Record<string, string> = { ...hardcodedNameMap };

      // 可选：尝试从外部文件补充/覆盖（如果需要动态更新）
      // try {
      //   const resName = await fetch(`${base}libs/uml-name-map.json?ts=${Date.now()}`, {
      //     cache: 'no-cache',
      //   });
      //   if (resName.ok) {
      //     const nameJson = await resName.json();
      //     if (nameJson && typeof nameJson === 'object') {
      //       nameMapLocal = { ...nameMapLocal, ...nameJson };
      //       setUmlNameMap(nameMapLocal);
      //     }
      //   }
      // } catch (err) {
      //   console.warn('Load UML name map failed', err);
      // }

      const res = await fetch(
        `${base}libs/UML-ER-library.excalidrawlib?ts=${Date.now()}`,
        { cache: 'no-cache' },
      );
      const data = await res.json();
      const libraryItemsRaw = data.libraryItems ?? data.library ?? [];
      if (!Array.isArray(libraryItemsRaw)) return;

      const mapToLibraryItem = (raw: any, idx: number) => {
        const nameFromRaw = (raw as any)?.name;

        const elements = Array.isArray(raw)
          ? raw
          : Array.isArray(raw?.elements)
            ? raw.elements
            : [];

        if (!Array.isArray(elements) || elements.length === 0) {
          return null;
        }

        const nameFromFirstElement = elements[0]?.name;
        const textLabel = (elements.find(
          (el: any) => el?.type === 'text' && typeof el.text === 'string' && el.text.trim(),
        )?.text || '').trim();

        const defaultName = String(idx + 1).padStart(2, '0');
        const key = (raw as any)?.id ?? String(idx);
        const label =
          (nameMapLocal[key] ?? nameMapLocal[String(idx)]) ??
          nameFromRaw ??
          nameFromFirstElement ??
          textLabel ??
          defaultName;

        return {
          id: raw?.id ?? `uml-${idx}`,
          status: raw?.status ?? 'published',
          name: raw?.name ?? label,
          label,
          elements,
          originalIndex: idx,
        };
      };

      // 过滤掉重复和无用的元素：1, 3, 13, 14, 15, 20
      const excludedIndices = new Set([1, 3, 13, 14, 15, 20]);
      
      const mapped = libraryItemsRaw
        .map(mapToLibraryItem)
        .filter((item: any) => item && !excludedIndices.has(item.originalIndex))
        .map((item: any, visIdx: number) => {
          const override = nameMapLocal[String(visIdx)];
          if (!override) return item;
          return {
            ...item,
            name: override,
            label: override,
          };
        });

      console.log('🔍 Name mapping:', nameMapLocal);
      console.log('📚 Mapped items (first 3):', mapped.slice(0, 3).map((x: any) => ({ id: x.id, name: x.name, label: x.label })));

      setUmlLibraryItems(mapped);

      if (mapped.length > 0) {
        excalidrawAPI.updateLibrary?.({
          libraryItems: mapped,
          openLibraryMenu: true,
        });
      }
    } catch (err) {
      console.error('Import UML-ER library failed', err);
    }
  }, [excalidrawAPI]);

  const handleInsertUmlItem = useCallback(
    (item: any) => {
      if (!excalidrawAPI || !item) return;
      const wrapped = item?.elements
        ? [item]
        : Array.isArray(item)
          ? [{ id: 'uml-tmp', status: 'published', elements: item }]
          : [];
      if (wrapped.length === 0) return;

      // 优先使用官方 API 插入库元素
      if (excalidrawAPI.insertLibraryItems) {
        excalidrawAPI.insertLibraryItems(wrapped);
        excalidrawAPI.setActiveTool?.({ type: 'selection' });
        return;
      }

      if (excalidrawAPI.addLibraryItems) {
        excalidrawAPI.addLibraryItems(wrapped);
        excalidrawAPI.setActiveTool?.({ type: 'selection' });
        return;
      }

      // 如果以上 API 不存在，手动将元素克隆进当前场景，避免弹出库面板
      const sceneEls = excalidrawAPI.getSceneElements?.() || [];
      const now = Date.now();
      const randId = () => `${now}-${Math.random().toString(36).slice(2, 8)}`;

      const appState = excalidrawAPI.getAppState?.();
      const zoom = appState?.zoom?.value ?? 1;
      const viewportWidth = appState?.width ?? 0;
      const viewportHeight = appState?.height ?? 0;
      const scrollX = appState?.scrollX ?? 0;
      const scrollY = appState?.scrollY ?? 0;

      // 计算库元素包围盒，用于居中到当前视口
      const elems = wrapped[0]?.elements || [];
      const bbox = elems.reduce(
        (acc: any, el: any) => {
          const x2 = el.x + el.width;
          const y2 = el.y + el.height;
          return {
            minX: Math.min(acc.minX, el.x),
            minY: Math.min(acc.minY, el.y),
            maxX: Math.max(acc.maxX, x2),
            maxY: Math.max(acc.maxY, y2),
          };
        },
        { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity },
      );

      const bboxCenterX = bbox.minX + (bbox.maxX - bbox.minX) / 2;
      const bboxCenterY = bbox.minY + (bbox.maxY - bbox.minY) / 2;

      const viewCenterX = (-scrollX) + viewportWidth / (2 * zoom);
      const viewCenterY = (-scrollY) + viewportHeight / (2 * zoom);

      const dx = isFinite(bboxCenterX) ? viewCenterX - bboxCenterX : 0;
      const dy = isFinite(bboxCenterY) ? viewCenterY - bboxCenterY : 0;

      // 为多元素库项生成统一的 groupId，确保插入后自动成组
      // 单元素库项清空 groupIds，避免多次插入相同元素时错误地共享 group
      const newGroupId = `group-${randId()}`;
      const shouldGroup = (wrapped[0]?.elements || []).length > 1;

      const cloned = (wrapped[0]?.elements || []).map((el: any, idx: number) => ({
        ...el,
        id: `${el.id || 'uml'}-${randId()}-${idx}`,
        version: 1,
        versionNonce: Math.floor(Math.random() * 1e9),
        seed: Math.floor(Math.random() * 1e9),
        isDeleted: false,
        x: el.x + dx,
        y: el.y + dy,
        // 多元素库项：分配新的 groupId 确保组合在一起
        // 单元素库项：清空 groupIds 确保每次插入都是独立元素
        groupIds: shouldGroup ? [newGroupId] : [],
      }));

      excalidrawAPI.updateScene?.({
        elements: [...sceneEls, ...cloned],
      });

      excalidrawAPI.setActiveTool?.({ type: 'selection' });
    },
    [excalidrawAPI],
  );

  // 自动加载 UML 库（用户已将文件放在 public/libs 下），免去手动点击菜单。
  useEffect(() => {
    if (!excalidrawAPI) return;
    handleImportUmlLibrary();
  }, [excalidrawAPI, handleImportUmlLibrary]);

  const toggleHistorySidebar = useCallback(() => {
    excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
  }, [excalidrawAPI]);

  // 撤销/重做/清空操作
  const handleUndo = useCallback(() => {
    excalidrawAPI?.history?.undo?.();
  }, [excalidrawAPI]);

  const handleRedo = useCallback(() => {
    excalidrawAPI?.history?.redo?.();
  }, [excalidrawAPI]);

  const handleClearCanvas = useCallback(() => {
    if (!excalidrawAPI) return;
    const allElements = excalidrawAPI.getSceneElements() || [];
    const deletedElements = allElements.map((el: any) => ({ ...el, isDeleted: true }));
    excalidrawAPI.updateScene({ elements: deletedElements });
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

          <MainMenu.Item
            onSelect={handleImportUmlLibrary}
            icon={<Boxes size={16} />}
          >
            导入 UML / ER 库
          </MainMenu.Item>

          {roomId && (
            <MainMenu.Item
              onSelect={toggleHistorySidebar}
              icon={<History size={16} />}
            >
              历史版本
            </MainMenu.Item>
          )}

          {roomId && !isMobile && (
            <MainMenu.Item
              onSelect={() => setIsAIOpen(!isAIOpen)}
              icon={<Bot size={16} />}
            >
              AI 助手
            </MainMenu.Item>
          )}

          {!isMobile && (
            <MainMenu.Item
              onSelect={() => setIsSettingsOpen(!isSettingsOpen)}
              icon={<Settings size={16} />}
            >
              模型设置
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

        {/* 设置侧边栏 */}
        {isSettingsOpen && !isMobile && (
          <ExcalidrawSidebar name="settings-panel" docked>
            <ExcalidrawSidebar.Header>
              <div className="flex items-center gap-2 px-2">
                <Settings size={18} />
                <span className="font-semibold">模型设置</span>
              </div>
            </ExcalidrawSidebar.Header>
            <SettingsPanel isDark={isDark} />
          </ExcalidrawSidebar>
        )}
      </Excalidraw>

      {/* ================= draw.io 风格 Palette ================= */}

      {toolPanelMode === 'shape' && (
        <ShapePalette
          excalidrawAPI={excalidrawAPI}
          isDark={isDark}
          umlLibraryItems={umlLibraryItems}
          onInsertUmlItem={handleInsertUmlItem}
        />
      )}

      {/* ================= AI 助手 ================= */}
      {roomId && !isMobile && (
        <AIAssistant
          roomId={roomId}
          isDark={isDark}
          isOpen={isAIOpen}
          onClose={() => setIsAIOpen(false)}
        />
      )}

      {/* ================= 移动端浮动按钮 ================= */}
      {isMobile && (
        <MobileFAB
          isDark={isDark}
          isConnected={true}
          isSynced={true}
          collaboratorsCount={0}
          onUndo={handleUndo}
          onRedo={handleRedo}
          onToggleTheme={() => useThemeStore.getState().toggleTheme()}
          onToggleHistory={toggleHistorySidebar}
          onClearCanvas={handleClearCanvas}
          onBackToRooms={handleBackToRooms}
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
