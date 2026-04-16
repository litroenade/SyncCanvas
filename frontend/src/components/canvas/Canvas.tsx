import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Excalidraw,
  MainMenu,
  Sidebar as ExcalidrawSidebar,
  CaptureUpdateAction,
  viewportCoordsToSceneCoords,
} from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import '@excalidraw/excalidraw/index.css';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import {
  buildViewportRepairAppState,
  filterFiniteSceneElements,
  normalizeViewportState,
} from '../../lib/excalidrawViewport';
import { getManagedDiagramStatusView } from '../../lib/managedDiagramStatus';
import { coalesceManagedSelection } from '../../lib/managedSelectionState';
import { useCanvas } from '../../hooks/useCanvas';
import { useThemeStore } from '../../stores/useThemeStore';
import { yjsManager, type ExcalidrawElement } from '../../lib/yjs';
import { applyManagedPreviewToCanvas } from '../../lib/managedPreviewApply';
import {
  consumeManagedPreviewDragPayload,
  getManagedPreviewDragToken,
  MANAGED_PREVIEW_APPLIED_EVENT,
  translateDiagramBundle,
  translatePreviewElementsToScenePoint,
} from '../../lib/managedPreviewDrag';
import type { ManagedDiagramTarget } from '../../types';
import { HistoryPanel } from './HistoryPanel';
import { MobileFAB } from './MobileFAB';
import { AISidebar } from '../ai/AISidebar';
import { ModelSettingsDialog } from '../common/ModelSettingsDialog';
import {
  History,
  Users,
  Wifi,
  WifiOff,
  Loader2,
  Sparkles,
  Settings,
  AlertTriangle,
  Languages,
  Moon,
  Sun,
} from 'lucide-react';

interface CanvasProps {
  roomId?: string;
  roomName?: string;
}

const HISTORY_SIDEBAR_NAME = 'history-panel';

const getDeviceInfo = () => {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const minDimension = Math.min(width, height);

  const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches;
  const isMobile = minDimension < 768 || (isTouchDevice && width < 1024);
  const isTablet = isTouchDevice && minDimension >= 768 && minDimension < 1024;

  return { isMobile, isTablet, isTouchDevice };
};

const useDeviceType = () => {
  const [deviceInfo, setDeviceInfo] = useState(() => {
    if (typeof window === 'undefined') {
      return { isMobile: false, isTablet: false, isTouchDevice: false };
    }
    return getDeviceInfo();
  });

  useEffect(() => {
    const handleResize = () => setDeviceInfo(getDeviceInfo());
    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, []);

  return deviceInfo;
};

export const Canvas: React.FC<CanvasProps> = ({ roomId, roomName }) => {
  const { theme, toggleTheme } = useThemeStore();
  const { t, excalidrawLanguage, locale, setLocale } = useI18n();
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const isRemoteUpdateRef = useRef(false);
  const managedSelectionRef = useRef<ManagedDiagramTarget | null>(null);
  const { isMobile, isTouchDevice } = useDeviceType();
  const [showAISidebar, setShowAISidebar] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [managedSelection, setManagedSelection] = useState<ManagedDiagramTarget | null>(null);

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
  type ExcalidrawOnChange = NonNullable<React.ComponentProps<typeof Excalidraw>['onChange']>;
  type CanvasElements = Parameters<ExcalidrawOnChange>[0];
  type CanvasAppState = Parameters<ExcalidrawOnChange>[1];
  type CanvasFiles = Parameters<ExcalidrawOnChange>[2];
  type HandleChangeElements = Parameters<typeof handleChange>[0];
  type HandleChangeAppState = Parameters<typeof handleChange>[1];
  type HandleChangeFiles = Parameters<typeof handleChange>[2];
  type UpdateSceneArgs = Parameters<ExcalidrawImperativeAPI['updateScene']>[0];
  type AddFilesArgs = Parameters<ExcalidrawImperativeAPI['addFiles']>[0];
  type ScrollToContentTarget = Parameters<ExcalidrawImperativeAPI['scrollToContent']>[0];

  const isDark = theme === 'dark';

  const updateManagedSelection = useCallback((nextSelection: ManagedDiagramTarget | null) => {
    setManagedSelection((previousSelection) => {
      const resolvedSelection = coalesceManagedSelection(previousSelection, nextSelection);
      managedSelectionRef.current = resolvedSelection;
      return resolvedSelection;
    });
  }, []);

  const handleExcalidrawAPI = useCallback((api: ExcalidrawImperativeAPI | null) => {
    setExcalidrawAPI((previousApi) => (previousApi === api ? previousApi : api));
  }, []);

  useEffect(() => {
    if (!excalidrawAPI) return;

    const sceneElements = filterFiniteSceneElements(elements as unknown as ExcalidrawElement[]);
    const viewportRepair = buildViewportRepairAppState(excalidrawAPI.getAppState());

    isRemoteUpdateRef.current = true;
    excalidrawAPI.updateScene({
      elements: sceneElements as unknown as UpdateSceneArgs['elements'],
      ...(viewportRepair
        ? { appState: viewportRepair as UpdateSceneArgs['appState'] }
        : {}),
      captureUpdate: CaptureUpdateAction.NEVER,
    });

    if (files && Object.keys(files).length > 0) {
      excalidrawAPI.addFiles(Object.values(files) as AddFilesArgs);
    }

    if ((viewportRepair || sceneElements.length !== elements.length) && sceneElements.length > 0) {
      excalidrawAPI.scrollToContent(sceneElements as unknown as ScrollToContentTarget, {
        fitToViewport: true,
        animate: false,
      });
    }

    const timeout = window.setTimeout(() => {
      isRemoteUpdateRef.current = false;
    }, 250);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [elements, excalidrawAPI, files]);

  const onExcalidrawChange = useCallback((
    newElements: CanvasElements,
    appState: CanvasAppState,
    newFiles: CanvasFiles,
  ) => {
    const syncedElements = newElements as unknown as HandleChangeElements;
    const syncedFiles = newFiles as unknown as HandleChangeFiles;
    const localSceneApply = yjsManager.consumeLocalSceneApply(
      syncedElements as unknown as readonly ExcalidrawElement[],
    );
    if (localSceneApply.applied) {
      if (localSceneApply.selection) {
        updateManagedSelection(localSceneApply.selection);
      }
      handleChange(syncedElements, appState as unknown as HandleChangeAppState, syncedFiles, {
        skipYjsSync: true,
        skipManagedReverseSync: true,
      });
      return;
    }

    const selectedIds = Object.keys(appState?.selectedElementIds || {});
    const nextSelection = yjsManager.resolveManagedSelection(
      selectedIds,
      managedSelectionRef.current,
      { preferExistingDiagram: isRemoteUpdateRef.current },
    );

    if (isRemoteUpdateRef.current) {
      updateManagedSelection(nextSelection);
      return;
    }

    handleChange(syncedElements, appState as unknown as HandleChangeAppState, syncedFiles);
    updateManagedSelection(
      nextSelection ? yjsManager.refreshManagedSelection(nextSelection) ?? nextSelection : null,
    );
  }, [handleChange, updateManagedSelection]);

  const onPointerUpdate = useCallback((payload: { pointer: { x: number; y: number }; button: 'up' | 'down' }) => {
    updatePointer(payload.pointer);
  }, [updatePointer]);

  const toggleHistorySidebar = useCallback(() => {
    excalidrawAPI?.toggleSidebar({ name: HISTORY_SIDEBAR_NAME });
  }, [excalidrawAPI]);

  const handleClearCanvas = useCallback(() => {
    excalidrawAPI?.resetScene();
  }, [excalidrawAPI]);

  const toggleLocale = useCallback(() => {
    setLocale(locale === 'zh-CN' ? 'en-US' : 'zh-CN');
  }, [locale, setLocale]);

  const handleManagedPreviewDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    const token = getManagedPreviewDragToken(event.dataTransfer);
    if (!token || !excalidrawAPI) {
      return;
    }
    event.preventDefault();

    const payload = consumeManagedPreviewDragPayload(token);
    if (!payload) {
      return;
    }

    const appState = normalizeViewportState(excalidrawAPI.getAppState());
    const scenePoint = viewportCoordsToSceneCoords(
      { clientX: event.clientX, clientY: event.clientY },
      {
        zoom: appState.zoom as Parameters<typeof viewportCoordsToSceneCoords>[1]['zoom'],
        offsetLeft: appState.offsetLeft,
        offsetTop: appState.offsetTop,
        scrollX: appState.scrollX,
        scrollY: appState.scrollY,
      },
    );
    const translated = translatePreviewElementsToScenePoint(payload.elements, scenePoint);
    const translatedBundle = payload.diagramBundle
      ? translateDiagramBundle(
        payload.diagramBundle,
        translated.deltaX,
        translated.deltaY,
        translated.elements,
      )
      : undefined;

    applyManagedPreviewToCanvas({
      excalidrawAPI,
      elementsToAdd: translated.elements,
      diagramBundle: translatedBundle,
      files: payload.files,
    });
    window.dispatchEvent(new CustomEvent(MANAGED_PREVIEW_APPLIED_EVENT, {
      detail: { messageId: payload.messageId },
    }));
  }, [excalidrawAPI]);

  const handleManagedPreviewDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    if (!getManagedPreviewDragToken(event.dataTransfer)) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  const generateIdForFile = useCallback(async (file: File): Promise<string> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: t('canvas.uploadFailed') }));
        throw new Error(error.detail || t('canvas.uploadFailed'));
      }

      const data = await response.json();
      return data.filename;
    } catch (error) {
      console.error('[Canvas] image upload failed:', error);
      return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }
  }, [t]);

  const renderTopRightUI = useCallback(() => {
    if (isMobile) return null;

    const StatusIcon = !isConnected ? WifiOff : (!isSynced ? Loader2 : Wifi);
    const statusText = !isConnected
      ? t('mobileFab.status.offline')
      : (!isSynced ? t('mobileFab.status.syncing') : t('mobileFab.status.connected'));
    const statusBg = !isConnected
      ? 'linear-gradient(135deg, #ef4444 0%, #f43f5e 100%)'
      : (!isSynced
        ? 'linear-gradient(135deg, #f59e0b 0%, #f97316 100%)'
        : 'linear-gradient(135deg, #10b981 0%, #14b8a6 100%)');
    const localeToggleTitle = locale === 'zh-CN'
      ? t('locale.switchToEnglish')
      : t('locale.switchToChinese');
    const localeToggleLabel = locale === 'zh-CN'
      ? t('locale.englishShort')
      : t('locale.chineseShort');

    return (
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {collaborators.size > 0 && (
          <div
            style={{
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
            }}
          >
            <Users size={13} strokeWidth={2.5} />
            <span>{collaborators.size + 1}</span>
          </div>
        )}

        <div
          style={{
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
          }}
        >
          <StatusIcon
            size={13}
            strokeWidth={2.5}
            style={!isSynced && isConnected ? { animation: 'spin 1s linear infinite' } : undefined}
          />
          <span>{statusText}</span>
        </div>

        <button
          type="button"
          onClick={toggleLocale}
          title={localeToggleTitle}
          aria-label={localeToggleTitle}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '999px',
            border: 'none',
            background: isDark ? 'rgba(39, 39, 42, 0.88)' : 'rgba(255, 255, 255, 0.92)',
            color: isDark ? '#f4f4f5' : '#27272a',
            fontSize: '12px',
            fontWeight: 600,
            boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
            cursor: 'pointer',
          }}
        >
          <Languages size={13} strokeWidth={2.5} />
          <span>{localeToggleLabel}</span>
        </button>
      </div>
    );
  }, [collaborators.size, isConnected, isSynced, isMobile, isDark, locale, t, toggleLocale]);

  const selectionBadgeVisible = managedSelection && managedSelection.mode !== 'create_new';
  const selectionStatus = getManagedDiagramStatusView(managedSelection);

  return (
    <div
      className="canvas-container"
      onDragOver={handleManagedPreviewDragOver}
      onDrop={handleManagedPreviewDrop}
    >
      {isMobile && (
        <MobileFAB
          isDark={isDark}
          isConnected={isConnected}
          isSynced={isSynced}
          collaboratorsCount={collaborators.size}
          locale={locale}
          onUndo={undo}
          onRedo={redo}
          onToggleLocale={toggleLocale}
          onToggleTheme={toggleTheme}
          onToggleHistory={toggleHistorySidebar}
          onClearCanvas={handleClearCanvas}
        />
      )}

      {!isMobile && roomId && (
        <div
          className={cn(
            'canvas-room-info glass-pill fixed z-[40] flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-300 pointer-events-none',
            isDark ? 'text-zinc-400' : 'text-zinc-500',
          )}
          style={{
            left: 'max(12px, env(safe-area-inset-left, 12px))',
            bottom: 'max(60px, env(safe-area-inset-bottom, 12px))',
          }}
        >
          <Sparkles size={12} className={isDark ? 'text-violet-400' : 'text-violet-500'} />
          <span className="max-w-[150px] truncate">
            {roomName || t('canvas.roomBadge', { id: roomId.slice(0, 8) })}
          </span>
        </div>
      )}

      {selectionBadgeVisible && (
        <div
          className={cn(
            'glass-pill fixed z-[40] rounded-2xl px-3 py-2 text-xs pointer-events-none',
            selectionStatus.severity === 'blocked'
              ? isDark
                ? 'text-amber-300'
                : 'text-amber-700'
              : selectionStatus.severity === 'warning'
                ? isDark
                  ? 'text-orange-200'
                  : 'text-orange-700'
                : isDark
                ? 'text-violet-300'
                : 'text-violet-700',
          )}
          style={{
            right: 'max(12px, env(safe-area-inset-right, 12px))',
            bottom: 'max(60px, env(safe-area-inset-bottom, 12px))',
          }}
        >
          <div className="flex items-center gap-2">
            {selectionStatus.severity !== 'normal' && <AlertTriangle size={12} />}
            <span className="font-semibold">
              {selectionStatus.headline}
            </span>
            {selectionStatus.metaItems.map((item) => (
              <span
                key={item}
                className={cn('opacity-80', item.includes('.') ? 'font-mono' : '')}
              >
                {item}
              </span>
            ))}
            {selectionStatus.warningSummary ? (
              <span className="opacity-80">{selectionStatus.warningSummary}</span>
            ) : null}
          </div>
          {selectionStatus.reason && (
            <div className="mt-1 opacity-90">{selectionStatus.reason}</div>
          )}
        </div>
      )}

      {roomId && !isMobile && (
        <AISidebar
          roomId={roomId}
          isDark={isDark}
          isOpen={showAISidebar}
          onToggle={() => setShowAISidebar((prev) => !prev)}
          excalidrawAPI={excalidrawAPI}
          diagramTarget={managedSelection}
        />
      )}

      <Excalidraw
        excalidrawAPI={handleExcalidrawAPI}
        initialData={{
          elements: [],
          appState: {
            zenModeEnabled: false,
            gridModeEnabled: false,
          },
        }}
        onChange={onExcalidrawChange}
        onPointerUpdate={isTouchDevice ? undefined : onPointerUpdate}
        theme={isDark ? 'dark' : 'light'}
        langCode={excalidrawLanguage}
        viewModeEnabled={false}
        zenModeEnabled={false}
        gridModeEnabled={false}
        renderTopRightUI={renderTopRightUI}
        generateIdForFile={generateIdForFile}
        UIOptions={{
          canvasActions: {
            loadScene: true,
            export: { saveFileToDisk: true },
            saveToActiveFile: true,
            clearCanvas: true,
            changeViewBackgroundColor: true,
            toggleTheme: false,
          },
          welcomeScreen: false,
        }}
      >
        {!isMobile && (
          <MainMenu>
            <MainMenu.DefaultItems.LoadScene />
            <MainMenu.DefaultItems.SaveToActiveFile />
            <MainMenu.DefaultItems.Export />
            <MainMenu.DefaultItems.SaveAsImage />
            <MainMenu.Separator />
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.Separator />
            {roomId && (
              <MainMenu.Item onSelect={toggleHistorySidebar} icon={<History size={16} />}>
                {t('canvas.menu.history')}
              </MainMenu.Item>
            )}
            <MainMenu.Item onSelect={() => setShowSettings(true)} icon={<Settings size={16} />}>
              {t('canvas.menu.modelSettings')}
            </MainMenu.Item>
            <MainMenu.Separator />
            <MainMenu.Item
              onSelect={toggleTheme}
              icon={isDark ? <Sun size={16} /> : <Moon size={16} />}
            >
              {isDark ? t('canvas.menu.lightMode') : t('canvas.menu.darkMode')}
            </MainMenu.Item>
            <MainMenu.DefaultItems.ChangeCanvasBackground />
          </MainMenu>
        )}

        {roomId && (
          <ExcalidrawSidebar name={HISTORY_SIDEBAR_NAME}>
            <ExcalidrawSidebar.Header>
              <div className="flex items-center gap-2 px-2">
                <History size={18} />
                <span className="font-semibold">{t('canvas.sidebar.history')}</span>
              </div>
            </ExcalidrawSidebar.Header>
            <div className="h-[calc(100%-50px)] overflow-auto p-2">
              <HistoryPanel roomId={roomId} />
            </div>
          </ExcalidrawSidebar>
        )}
      </Excalidraw>

      <ModelSettingsDialog
        open={showSettings}
        onClose={() => setShowSettings(false)}
        isDark={isDark}
      />
    </div>
  );
};
