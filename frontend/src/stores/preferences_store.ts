import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * 偏好设置状态接口
 */
interface PreferencesState {
  /** 图标集 ID */
  iconSetId: string
  /** 设置图标集 ID */
  setIconSetId: (id: string) => void
  /** 是否启用快捷键 */
  shortcutsEnabled: boolean
  /** 设置是否启用快捷键 */
  setShortcutsEnabled: (enabled: boolean) => void
}

const STORAGE_KEY = 'whiteboard-preferences'
const DEFAULT_ICON_SET = 'classic'
const DEFAULT_SHORTCUTS_ENABLED = true

/**
 * 偏好设置状态管理 (Zustand + Persist)
 * 
 * 自动持久化到 localStorage。
 */
export const usePreferencesStore = create<PreferencesState>()(persist(
  (set) => ({
    iconSetId: DEFAULT_ICON_SET,
    setIconSetId: (id: string) => set({ iconSetId: id }),
    shortcutsEnabled: DEFAULT_SHORTCUTS_ENABLED,
    setShortcutsEnabled: (enabled: boolean) => set({ shortcutsEnabled: enabled }),
  }),
  {
    name: STORAGE_KEY,
  },
))

