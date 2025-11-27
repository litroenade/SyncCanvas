import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { config } from '../config/env';

// 创建单例 Yjs 文档
export const ydoc = new Y.Doc();

// 创建单例 WebsocketProvider
// 我们目前使用固定的房间名称
export const provider = new WebsocketProvider(
    config.wsBaseUrl,
    'default-room',
    ydoc
);

export const shapesMap = ydoc.getMap('shapes');

// 创建 UndoManager，追踪 shapesMap 的变化
export const undoManager = new Y.UndoManager(shapesMap);

provider.on('status', (event: { status: string }) => {
    console.log('Yjs 连接状态:', event.status);
});
