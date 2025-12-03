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
