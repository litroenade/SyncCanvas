/**
 * Yjs 房间管理器 - 精简版
 */
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { config } from '../config/env';

class YjsRoomManager {
    private _roomId: string | null = null;
    private _ydoc: Y.Doc | null = null;
    private _provider: WebsocketProvider | null = null;
    private _shapesMap: Y.Map<any> | null = null;
    private _undoManager: Y.UndoManager | null = null;

    get roomId() { return this._roomId; }
    get ydoc() { return this._ydoc; }
    get provider() { return this._provider; }
    get shapesMap() { return this._shapesMap; }
    get undoManager() { return this._undoManager; }
    get isConnected() { return this._provider !== null; }
    get isWsConnected() { return this._provider?.wsconnected ?? false; }

    getAwareness() { return this._provider?.awareness; }

    connect(roomId: string): void {
        // 已连接同一房间，跳过
        if (this._roomId === roomId && this._provider) return;

        // 断开旧连接（同步）
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

        this._shapesMap = this._ydoc.getMap('shapes');
        this._undoManager = new Y.UndoManager(this._shapesMap);
    }

    disconnect(): void {
        this._cleanup();
    }

    private _listeners: (() => void)[] = [];

    onDocChange(listener: () => void) {
        this._listeners.push(listener);
    }

    offDocChange(listener: () => void) {
        this._listeners = this._listeners.filter(l => l !== listener);
    }

    private _notify() {
        this._listeners.forEach(l => l());
    }

    previewData(data: ArrayBuffer) {
        if (!this._roomId) return;
        const roomId = this._roomId;

        // 清理当前连接和文档
        this._cleanup();

        // 恢复 roomId
        this._roomId = roomId;

        // 创建新文档并应用数据
        this._ydoc = new Y.Doc();
        Y.applyUpdate(this._ydoc, new Uint8Array(data));

        this._shapesMap = this._ydoc.getMap('shapes');
        this._undoManager = new Y.UndoManager(this._shapesMap);

        // 通知监听者文档已更改
        this._notify();
    }

    exitPreview() {
        if (!this._roomId) return;
        const roomId = this._roomId;

        // 重新连接 (会自动清理并创建新文档)
        this.connect(roomId);

        // 通知监听者
        this._notify();
    }

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
        this._shapesMap = null;
        this._undoManager = null;
        this._roomId = null;
    }
}

export const yjsManager = new YjsRoomManager();
