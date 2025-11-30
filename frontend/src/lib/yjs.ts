import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { config } from '../config/env';
import { roomsApi } from '../services/api/rooms';

// 空闲检测配置
const IDLE_TIMEOUT = 5 * 60 * 1000; // 5分钟无操作视为空闲
const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'wheel'];

// 动态房间管理器
class YjsRoomManager {
    private currentRoomId: string | null = null;
    private _ydoc: Y.Doc | null = null;
    private _provider: WebsocketProvider | null = null;
    private _shapesMap: Y.Map<any> | null = null;
    private _undoManager: Y.UndoManager | null = null;
    
    // 空闲检测
    private _idleTimer: ReturnType<typeof setTimeout> | null = null;
    private _activityHandler: (() => void) | null = null;
    private _hasUnsavedChanges: boolean = false;
    private _isAutoCommitting: boolean = false;

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

        // 监听文档更改，标记有未保存的更改
        this._shapesMap.observeDeep(() => {
            this._hasUnsavedChanges = true;
            // 重置空闲计时器
            this._resetIdleTimer();
        });

        this.currentRoomId = roomId;
        
        // 启动空闲检测
        this._startIdleDetection();
    }

    /**
     * 断开当前房间连接
     */
    async disconnect(): Promise<void> {
        // 停止空闲检测
        this._stopIdleDetection();
        
        // 如果有未保存的更改，尝试自动提交
        if (this.currentRoomId && this._hasUnsavedChanges && !this._isAutoCommitting) {
            await this._autoCommit('Auto save on disconnect');
        }

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
        this._hasUnsavedChanges = false;
    }

    /**
     * 获取 Awareness 实例
     */
    getAwareness() {
        return this._provider?.awareness;
    }

    /**
     * 启动空闲检测
     */
    private _startIdleDetection(): void {
        // 创建活动处理器
        this._activityHandler = () => {
            // 重置空闲计时器
            this._resetIdleTimer();
        };
        
        // 监听用户活动事件
        ACTIVITY_EVENTS.forEach(event => {
            document.addEventListener(event, this._activityHandler!, { passive: true });
        });
        
        // 启动空闲计时器
        this._resetIdleTimer();
        
        console.log('空闲检测已启动');
    }

    /**
     * 停止空闲检测
     */
    private _stopIdleDetection(): void {
        // 清除计时器
        if (this._idleTimer) {
            clearTimeout(this._idleTimer);
            this._idleTimer = null;
        }
        
        // 移除事件监听器
        if (this._activityHandler) {
            ACTIVITY_EVENTS.forEach(event => {
                document.removeEventListener(event, this._activityHandler!);
            });
            this._activityHandler = null;
        }
        
        console.log('空闲检测已停止');
    }

    /**
     * 重置空闲计时器
     */
    private _resetIdleTimer(): void {
        if (this._idleTimer) {
            clearTimeout(this._idleTimer);
        }
        
        this._idleTimer = setTimeout(() => {
            this._onIdle();
        }, IDLE_TIMEOUT);
    }

    /**
     * 空闲时触发
     */
    private async _onIdle(): Promise<void> {
        if (this._hasUnsavedChanges && this.currentRoomId && !this._isAutoCommitting) {
            console.log('检测到空闲，触发自动提交');
            await this._autoCommit('Auto save on idle');
        }
        
        // 继续监测
        this._resetIdleTimer();
    }

    /**
     * 自动提交
     */
    private async _autoCommit(message: string): Promise<void> {
        if (!this.currentRoomId || this._isAutoCommitting) return;
        
        try {
            this._isAutoCommitting = true;
            console.log(`自动提交: ${message}`);
            
            await roomsApi.createCommit(this.currentRoomId, {
                message,
                author_name: localStorage.getItem('username') || 'Anonymous'
            });
            
            this._hasUnsavedChanges = false;
            console.log('自动提交成功');
        } catch (error) {
            // 忽略 400 错误 (没有数据可提交)
            if ((error as any)?.response?.status !== 400) {
                console.error('自动提交失败:', error);
            }
        } finally {
            this._isAutoCommitting = false;
        }
    }

    /**
     * 手动标记有更改
     */
    markDirty(): void {
        this._hasUnsavedChanges = true;
    }

    /**
     * 检查是否有未保存的更改
     */
    get hasUnsavedChanges(): boolean {
        return this._hasUnsavedChanges;
    }
}

// 导出单例实例
export const yjsManager = new YjsRoomManager();

// 页面关闭时的处理
// 使用 sendBeacon 发送同步请求，确保数据在页面关闭前发送
window.addEventListener('beforeunload', (event) => {
    if (yjsManager.hasUnsavedChanges && yjsManager.roomId) {
        // 使用 sendBeacon 发送自动提交请求
        const token = localStorage.getItem('token');
        const username = localStorage.getItem('username') || 'Anonymous';
        const roomId = yjsManager.roomId;
        
        const data = JSON.stringify({
            message: 'Auto save on page close',
            author_name: username
        });
        
        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        // sendBeacon 不支持自定义 headers，使用 fetch with keepalive
        fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/rooms/${roomId}/commit`, {
            method: 'POST',
            headers,
            body: data,
            keepalive: true  // 确保请求在页面关闭后继续
        }).catch(() => {
            // 忽略错误，页面即将关闭
        });
        
        // 显示确认对话框 (可选，某些浏览器会忽略)
        event.preventDefault();
        event.returnValue = '';
    }
});

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
