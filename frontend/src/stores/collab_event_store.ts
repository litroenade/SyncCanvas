/**
 * 协作事件流 Store
 */
import { create } from 'zustand'
import type { CollabEvent, CollabEventType } from '../types'

interface CollabEventState {
  events: CollabEvent[]
  memberFilter: 'all' | string
  typeFilter: Set<CollabEventType> | null
  addEvents: (list: CollabEvent[]) => void
  clear: () => void
  setMemberFilter: (value: 'all' | string) => void
  toggleType: (type: CollabEventType) => void
}

const MAX_EVENTS = 20

export const useCollabEventStore = create<CollabEventState>((set) => ({
  events: [],
  memberFilter: 'all',
  typeFilter: null,
  addEvents: (list) => set((state) => {
    if (!list.length) return state
    const merged = [...state.events, ...list].slice(-MAX_EVENTS)
    return { ...state, events: merged }
  }),
  clear: () => set({ events: [] }),
  setMemberFilter: (value) => set({ memberFilter: value }),
  toggleType: (type) => set((state) => {
    const next = state.typeFilter ? new Set(state.typeFilter) : new Set<CollabEventType>()
    if (next.has(type)) {
      next.delete(type)
    } else {
      next.add(type)
    }
    return { ...state, typeFilter: next.size ? next : null }
  }),
}))
