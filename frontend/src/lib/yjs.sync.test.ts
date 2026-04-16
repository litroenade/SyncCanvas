import * as Y from 'yjs';
import { describe, expect, it } from 'vitest';

import { ExcalidrawYjsManager } from './yjs';

function createManager(): ExcalidrawYjsManager {
  const manager = new ExcalidrawYjsManager();
  const internal = manager as unknown as {
    _roomId: string | null;
    _ydoc: Y.Doc | null;
    _attachMaps: () => void;
  };

  internal._roomId = 'room-test';
  internal._ydoc = new Y.Doc();
  internal._attachMaps();
  return manager;
}

describe('ExcalidrawYjsManager syncElements', () => {
  it('removes stale keys when an existing element drops optional properties', () => {
    const manager = createManager();

    manager.syncElements([
      {
        id: 'node-1',
        type: 'rectangle',
        x: 10,
        y: 20,
        width: 100,
        height: 40,
        groupIds: ['group-a'],
        customData: {
          syncCanvas: {
            diagramId: 'diagram-alpha',
            semanticId: 'diagram-alpha.node',
            role: 'block',
          },
        },
      },
    ]);

    manager.syncElements([
      {
        id: 'node-1',
        type: 'rectangle',
        x: 10,
        y: 20,
        width: 100,
        height: 40,
      },
    ]);

    const [synced] = manager.getElements();
    expect(synced).toBeDefined();
    expect('groupIds' in synced).toBe(false);
    expect('customData' in synced).toBe(false);
  });
});
