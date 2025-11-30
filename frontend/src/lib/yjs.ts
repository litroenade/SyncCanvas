import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { config } from '../config/env';

// 动态房间管理器
class YjsRoomManager {
    private currentRoomId: string | null = null;
    private _ydoc: Y.Doc | null = null;
    private _provider: WebsocketProvider | null = null;
    private _shapesMap: Y.Map<any> | null = null;
    private _undoManager: Y.UndoManager | null = null;

    get ydoc(): Y.Doc {
        if (!this._ydoc) {
            throw new Error('Yjs 文档未初始化，请先连接到房间');
        }
        return this._ydoc;
    }

    get provider(): WebsocketProvider {
        if (!this._provider) {
            throw new Error('WebSocket 提供器未初始化，请先连接到房间');
        }
        return this._provider;
    }

    get shapesMap(): Y.Map<any> {
        if (!this._shapesMap) {
            throw new Error('图形Map未初始化，请先连接到房间');
        }
        return this._shapesMap;
    }

    get undoManager(): Y.UndoManager {
        if (!this._undoManager) {
            throw new Error('UndoManager未初始化，请先连接到房间');
        }
        return this._undoManager;
    }

    get isConnected(): boolean {
        return this._provider !== null && this._provider.wsconnected;
    }

    get roomId(): string | null {
        return this.currentRoomId;
    }

    /**
     * 连接到指定房间
     */
    connect(roomId: string): void {
        // 如果已经连接到同一房间，不做任何事
        if (this.currentRoomId === roomId && this._provider) {
            console.log(`已连接到房间: ${roomId}`);
            return;
        }

        // 断开当前连接
        this.disconnect();

        console.log(`正在连接到房间: ${roomId}`);

        // 创建新的 Yjs 文档
        this._ydoc = new Y.Doc();
        
        // 获取认证 token
        const token = localStorage.getItem('token');
        
        // 创建 WebSocket 连接，URL 中包含房间 ID
        this._provider = new WebsocketProvider(
            config.wsBaseUrl,
            roomId,
            this._ydoc,
            {
                params: token ? { token } : undefined
            }
        );

        // 获取图形 Map
        this._shapesMap = this._ydoc.getMap('shapes');
        
        // 创建 UndoManager
        this._undoManager = new Y.UndoManager(this._shapesMap);

        // 监听连接状态
        this._provider.on('status', (event: { status: string }) => {
            console.log(`房间 ${roomId} 连接状态:`, event.status);
        });

        this._provider.on('sync', (isSynced: boolean) => {
            console.log(`房间 ${roomId} 同步状态:`, isSynced ? '已同步' : '同步中');
        });

        this.currentRoomId = roomId;
    }

    /**
     * 断开当前房间连接
     */
    disconnect(): void {
        if (this._provider) {
            console.log(`断开房间连接: ${this.currentRoomId}`);
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
        this.currentRoomId = null;
    }

    /**
     * 获取 Awareness 实例
     */
    getAwareness() {
        return this._provider?.awareness;
    }
}

// 导出单例实例
export const yjsManager = new YjsRoomManager();

// 为了向后兼容，导出代理对象
// 这些在未连接时会抛出错误，提醒开发者先连接到房间
export const ydoc = new Proxy({} as Y.Doc, {
    get(_, prop) {
        return (yjsManager.ydoc as any)[prop];
    }
});

export const provider = new Proxy({} as WebsocketProvider, {
    get(_, prop) {
        return (yjsManager.provider as any)[prop];
    }
});

export const shapesMap = new Proxy({} as Y.Map<any>, {
    get(_, prop) {
        const target = yjsManager.shapesMap;
        const value = (target as any)[prop];
        if (typeof value === 'function') {
            return value.bind(target);
        }
        return value;
    }
});

export const undoManager = new Proxy({} as Y.UndoManager, {
    get(_, prop) {
        return (yjsManager.undoManager as any)[prop];
    }
});
