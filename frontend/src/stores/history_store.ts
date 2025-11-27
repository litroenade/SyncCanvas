import { create } from 'zustand'
import type { WhiteboardElement } from '../types'

/**
 * 历史记录状态接口
 */
interface HistoryState {
  /** 撤销栈 */
  undoStack: WhiteboardElement[][]
  /** 重做栈 */
  redoStack: WhiteboardElement[][]
  /** 推送快照 */
  pushSnapshot: (snapshot: WhiteboardElement[]) => void
  /** 执行撤销 */
  undo: () => WhiteboardElement[] | null
  /** 执行重做 */
  redo: () => WhiteboardElement[] | null
  /** 是否可撤销 */
  canUndo: () => boolean
  /** 是否可重做 */
  canRedo: () => boolean
  /** 清空历史 */
  clear: () => void
}

const MAX_HISTORY = 50

/**
 * 历史记录状态管理 (Zustand)
 * 
 * 管理撤销/重做栈。
 */
export const useHistoryStore = create<HistoryState>((set, get) => ({
  undoStack: [],
  redoStack: [],

  pushSnapshot: (snapshot: WhiteboardElement[]) => {
    const { undoStack } = get()
    const newStack = [...undoStack, snapshot].slice(-MAX_HISTORY)
    set({ undoStack: newStack, redoStack: [] })
  },

  undo: () => {
    const { undoStack, redoStack } = get()
    if (undoStack.length <= 1) {
      return null
    }

    const current = undoStack[undoStack.length - 1]
    const previous = undoStack[undoStack.length - 2]

    const newUndoStack = undoStack.slice(0, -1)
    const newRedoStack = [...redoStack, current]

    set({ undoStack: newUndoStack, redoStack: newRedoStack })
    return previous
  },

  redo: () => {
    const { undoStack, redoStack } = get()
    if (redoStack.length === 0) {
      return null
    }

    const next = redoStack[redoStack.length - 1]
    const newRedoStack = redoStack.slice(0, -1)
    const newUndoStack = [...undoStack, next]

    set({ undoStack: newUndoStack, redoStack: newRedoStack })
    return next
  },

  canUndo: () => get().undoStack.length > 0,
  canRedo: () => get().redoStack.length > 0,
  clear: () => set({ undoStack: [], redoStack: [] }),
}))

