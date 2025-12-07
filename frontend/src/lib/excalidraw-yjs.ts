/**
 * 模块名称：ExcalidrawYjsManager
 * 主要功能：Excalidraw 与 Yjs 的双向同步管理器
 * 
 * 使用 Y.Array 存储 Excalidraw 元素，实现实时协作。
 */
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { config } from '../config/env';

// Excalidraw 元素类型定义（简化版，避免类型导入问题）
export interface ExcalidrawElement {
    id: string;
    type: string;
    x: number;
    y: number;
    width: number;
    height: number;
    isDeleted?: boolean;
    [key: string]: unknown;
}

export interface BinaryFileData {
    id: string;
    dataURL: string;
    created: number;
    mimeType: string;
    [key: string]: unknown;
}

export type BinaryFiles = Record<string, BinaryFileData>;

/**
 * Excalidraw Yjs 房间管理器
 * 
 * 管理与后端的 WebSocket 连接，同步 Excalidraw 元素到 Y.Array
 */
class ExcalidrawYjsManager {
    private _roomId: string | null = null;
    private _ydoc: Y.Doc | null = null;
    private _provider: WebsocketProvider | null = null;
    private _elementsArray: Y.Array<Y.Map<unknown>> | null = null;
    private _filesMap: Y.Map<string> | null = null;
    private _undoManager: Y.UndoManager | null = null;
    private _listeners: (() => void)[] = [];

    get roomId() { return this._roomId; }
    get ydoc() { return this._ydoc; }
    get provider() { return this._provider; }
    get elementsArray() { return this._elementsArray; }
    get filesMap() { return this._filesMap; }
    get undoManager() { return this._undoManager; }
    get isConnected() { return this._provider !== null; }
    get isWsConnected() { return this._provider?.wsconnected ?? false; }

    getAwareness() { return this._provider?.awareness; }

    /**
     * 连接到指定房间
     * @param roomId - 房间 ID
     */
    connect(roomId: string): void {
        // 已连接同一房间，跳过
        if (this._roomId === roomId && this._provider) return;

        // 断开旧连接
        this._cleanup();

        this._roomId = roomId;
        this._ydoc = new Y.Doc();

        const token = localStorage.getItem('token');
        this._provider = new WebsocketProvider(
            config.wsBaseUrl,
            roomId,
            this._ydoc,
            { params: token ? { token } : undefined }
        );

        // 使用 Y.Array 存储 Excalidraw 元素
        this._elementsArray = this._ydoc.getArray('elements');
        this._filesMap = this._ydoc.getMap('files');
        this._undoManager = new Y.UndoManager(this._elementsArray);
    }

    /**
     * 断开连接
     */
    disconnect(): void {
        this._cleanup();
    }

    /**
     * 注册文档变更监听器
     */
    onDocChange(listener: () => void) {
        this._listeners.push(listener);
    }

    /**
     * 取消文档变更监听器
     */
    offDocChange(listener: () => void) {
        this._listeners = this._listeners.filter(l => l !== listener);
    }

    private _notify() {
        this._listeners.forEach(l => l());
    }

    /**
     * 从 Y.Array 获取所有元素
     */
    getElements(): ExcalidrawElement[] {
        if (!this._elementsArray) return [];
        
        return this._elementsArray.toArray().map(yMap => {
            const obj: Record<string, unknown> = {};
            yMap.forEach((value, key) => {
                obj[key] = value;
            });
            return obj as unknown as ExcalidrawElement;
        });
    }

    /**
     * 根据 ID 查找元素在数组中的索引
     */
    private _findElementIndex(id: string): number {
        if (!this._elementsArray) return -1;
        
        for (let i = 0; i < this._elementsArray.length; i++) {
            const yMap = this._elementsArray.get(i);
            if (yMap.get('id') === id) {
                return i;
            }
        }
        return -1;
    }

    /**
     * 将 ExcalidrawElement 转换为 Y.Map
     */
    private _elementToYMap(element: ExcalidrawElement): Y.Map<unknown> {
        const yMap = new Y.Map<unknown>();
        Object.entries(element).forEach(([key, value]) => {
            // 对于嵌套对象和数组，直接存储（Yjs 会自动处理）
            yMap.set(key, value);
        });
        return yMap;
    }

    /**
     * 同步 Excalidraw 元素到 Yjs
     * 使用增量更新策略：比较本地和远程状态，只更新变化的部分
     */
    syncElements(elements: readonly ExcalidrawElement[]): void {
        if (!this._ydoc || !this._elementsArray) return;

        this._ydoc.transact(() => {
            const existingIds = new Set<string>();
            
            // 1. 收集现有元素的 ID
            this._elementsArray!.forEach((yMap) => {
                const id = yMap.get('id') as string;
                if (id) existingIds.add(id);
            });

            // 2. 更新或添加元素
            const newIds = new Set<string>();
            elements.forEach((element) => {
                newIds.add(element.id);
                const index = this._findElementIndex(element.id);
                
                if (index >= 0) {
                    // 更新现有元素
                    const yMap = this._elementsArray!.get(index);
                    Object.entries(element).forEach(([key, value]) => {
                        const currentValue = yMap.get(key);
                        // 只更新变化的属性（简单比较）
                        if (JSON.stringify(currentValue) !== JSON.stringify(value)) {
                            yMap.set(key, value);
                        }
                    });
                } else {
                    // 添加新元素
                    const yMap = this._elementToYMap(element);
                    this._elementsArray!.push([yMap]);
                }
            });

            // 3. 删除不再存在的元素
            for (let i = this._elementsArray!.length - 1; i >= 0; i--) {
                const yMap = this._elementsArray!.get(i);
                const id = yMap.get('id') as string;
                if (id && !newIds.has(id)) {
                    this._elementsArray!.delete(i, 1);
                }
            }
        }, 'excalidraw-sync');
    }

    /**
     * 获取所有文件
     */
    getFiles(): BinaryFiles {
        if (!this._filesMap) return {};
        
        const files: BinaryFiles = {};
        this._filesMap.forEach((jsonStr, key) => {
            try {
                files[key] = JSON.parse(jsonStr);
            } catch (e) {
                console.error('Failed to parse file data', e);
            }
        });
        return files;
    }

    /**
     * 同步文件到 Yjs
     */
    syncFiles(files: BinaryFiles): void {
        if (!this._ydoc || !this._filesMap) return;

        this._ydoc.transact(() => {
            Object.entries(files).forEach(([id, fileData]) => {
                if (!this._filesMap!.has(id)) {
                    // 只添加不存在的文件，文件内容通常不可变
                    this._filesMap!.set(id, JSON.stringify(fileData));
                }
            });
        }, 'excalidraw-files-sync');
    }

    /**
     * 添加单个元素
     */
    addElement(element: ExcalidrawElement): void {
        if (!this._ydoc || !this._elementsArray) return;

        this._ydoc.transact(() => {
            const yMap = this._elementToYMap(element);
            this._elementsArray!.push([yMap]);
        }, 'excalidraw-add');
    }

    /**
     * 更新单个元素
     */
    updateElement(id: string, updates: Partial<ExcalidrawElement>): void {
        if (!this._ydoc || !this._elementsArray) return;

        const index = this._findElementIndex(id);
        if (index < 0) return;

        this._ydoc.transact(() => {
            const yMap = this._elementsArray!.get(index);
            Object.entries(updates).forEach(([key, value]) => {
                yMap.set(key, value);
            });
        }, 'excalidraw-update');
    }

    /**
     * 删除元素
     */
    deleteElements(ids: string[]): void {
        if (!this._ydoc || !this._elementsArray) return;

        const idSet = new Set(ids);
        
        this._ydoc.transact(() => {
            for (let i = this._elementsArray!.length - 1; i >= 0; i--) {
                const yMap = this._elementsArray!.get(i);
                const id = yMap.get('id') as string;
                if (id && idSet.has(id)) {
                    this._elementsArray!.delete(i, 1);
                }
            }
        }, 'excalidraw-delete');
    }

    /**
     * 清空所有元素
     */
    clearElements(): void {
        if (!this._ydoc || !this._elementsArray) return;

        this._ydoc.transact(() => {
            this._elementsArray!.delete(0, this._elementsArray!.length);
        }, 'excalidraw-clear');
    }

    /**
     * 预览历史数据
     */
    previewData(data: ArrayBuffer): void {
        if (!this._roomId) return;
        const roomId = this._roomId;

        this._cleanup();
        this._roomId = roomId;

        this._ydoc = new Y.Doc();
        Y.applyUpdate(this._ydoc, new Uint8Array(data));

        this._elementsArray = this._ydoc.getArray('elements');
        this._filesMap = this._ydoc.getMap('files');
        this._undoManager = new Y.UndoManager(this._elementsArray);

        this._notify();
    }

    /**
     * 退出预览模式
     */
    exitPreview(): void {
        if (!this._roomId) return;
        const roomId = this._roomId;

        this.connect(roomId);
        this._notify();
    }

    /**
     * 清理资源
     */
    private _cleanup(): void {
        if (this._provider) {
            this._provider.disconnect();
            this._provider.destroy();
            this._provider = null;
        }
        if (this._ydoc) {
            this._ydoc.destroy();
            this._ydoc = null;
        }
        this._elementsArray = null;
        this._filesMap = null;
        this._undoManager = null;
        this._roomId = null;
    }
}

export const excalidrawYjsManager = new ExcalidrawYjsManager();
