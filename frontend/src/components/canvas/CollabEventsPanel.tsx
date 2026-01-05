import { useEffect, useMemo, useRef } from 'react'
import { useCollabEventStore } from '../../stores/collab_event_store'
import type { CollabEvent, CollabEventType } from '../../types'
import { cn } from '../../lib/utils'

const typeLabels: Record<CollabEventType, string> = {
  add: '新增',
  delete: '删除',
  update: '更新',
}

const typeColors: Record<CollabEventType, string> = {
  add: 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-100 dark:border-emerald-800/60',
  delete: 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/40 dark:text-rose-100 dark:border-rose-800/60',
  update: 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-50 dark:border-amber-800/60',
}

const getColorFromName = (name: string) => {
  const palette = ['#8b5cf6', '#2563eb', '#0ea5e9', '#22c55e', '#eab308', '#f97316', '#ef4444']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return palette[Math.abs(hash) % palette.length]
}

const formatTime = (ts: number) => new Date(ts).toLocaleTimeString()

const EventItem = ({ event }: { event: CollabEvent }) => {
  const color = getColorFromName(event.actorName)
  return (
    <div className="flex gap-3 py-2 px-3 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0"
        style={{ backgroundColor: color }}
        title={event.actorName}
      >
        {event.actorName.slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <span>{event.isMe ? '我' : event.actorName}</span>
          <span className={cn('text-[11px] px-2 py-[2px] rounded-full border', typeColors[event.type])}>
            {typeLabels[event.type]}
          </span>
          <span className="text-[11px] text-zinc-400 dark:text-zinc-500">{event.elementType}</span>
          <span className="text-[11px] text-zinc-400 dark:text-zinc-500 ml-auto">{formatTime(event.ts)}</span>
        </div>
        <div className="text-[13px] text-zinc-600 dark:text-zinc-300 mt-1 line-clamp-2">{event.summary}</div>
      </div>
    </div>
  )
}

export const CollabEventsPanel = () => {
  const { events, memberFilter, typeFilter, setMemberFilter, toggleType } = useCollabEventStore()
  const listRef = useRef<HTMLDivElement | null>(null)

  const members = useMemo(() => {
    const map = new Map<string, string>()
    events.forEach((e) => {
      if (!map.has(e.actorId)) {
        map.set(e.actorId, e.actorName)
      }
    })
    return Array.from(map.entries())
  }, [events])

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (memberFilter !== 'all' && e.actorId !== memberFilter) return false
      if (typeFilter && !typeFilter.has(e.type)) return false
      return true
    })
  }, [events, memberFilter, typeFilter])

  useEffect(() => {
    const el = listRef.current
    if (!el) return
    if (el.scrollTop < 24) {
      el.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [events.length])

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/80">
        <div className="flex items-center gap-2 mb-3">
          <select
            value={memberFilter}
            onChange={(e) => setMemberFilter(e.target.value)}
            className="text-sm border border-zinc-200 dark:border-zinc-700 rounded-md px-2 py-1 bg-white dark:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">所有成员</option>
            {members.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <div className="flex items-center gap-2 ml-auto">
            {(['add', 'delete', 'update'] as CollabEventType[]).map((t) => {
              const active = !typeFilter || typeFilter.has(t)
              return (
                <button
                  key={t}
                  onClick={() => toggleType(t)}
                  className={cn(
                    'text-xs px-2 py-1 rounded-md border transition-colors',
                    active
                      ? 'bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/40 dark:text-blue-100 dark:border-blue-800/60'
                      : 'bg-white text-zinc-500 border-zinc-200 dark:bg-zinc-900 dark:text-zinc-400 dark:border-zinc-700'
                  )}
                >
                  {typeLabels[t]}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div ref={listRef} className="flex-1 overflow-auto">
        {filtered.length === 0 && (
          <div className="p-6 text-sm text-zinc-400 dark:text-zinc-500 text-center">暂无事件</div>
        )}
        {filtered.map((event) => (
          <EventItem key={event.id} event={event} />
        ))}
      </div>
    </div>
  )
}
