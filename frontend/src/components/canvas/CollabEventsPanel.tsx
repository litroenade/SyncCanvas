import { useEffect, useMemo, useRef } from 'react'

import { useI18n } from '../../i18n'
import { cn } from '../../lib/utils'
import { useCollabEventStore } from '../../stores/collab_event_store'
import type { CollabEvent, CollabEventType } from '../../types'

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

interface EventItemProps {
  event: CollabEvent
  typeLabels: Record<CollabEventType, string>
  meLabel: string
  formatTime: (timestamp: number) => string
}

const EventItem = ({ event, typeLabels, meLabel, formatTime }: EventItemProps) => {
  const color = getColorFromName(event.actorName)

  return (
    <div className="flex gap-3 border-b border-zinc-100 px-3 py-2 last:border-0 dark:border-zinc-800">
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
        style={{ backgroundColor: color }}
        title={event.actorName}
      >
        {event.actorName.slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <span>{event.isMe ? meLabel : event.actorName}</span>
          <span className={cn('rounded-full border px-2 py-[2px] text-[11px]', typeColors[event.type])}>
            {typeLabels[event.type]}
          </span>
          <span className="text-[11px] text-zinc-400 dark:text-zinc-500">{event.elementType}</span>
          <span className="ml-auto text-[11px] text-zinc-400 dark:text-zinc-500">
            {formatTime(event.ts)}
          </span>
        </div>
        <div className="mt-1 line-clamp-2 text-[13px] text-zinc-600 dark:text-zinc-300">
          {event.summary}
        </div>
      </div>
    </div>
  )
}

export const CollabEventsPanel = () => {
  const { t, locale } = useI18n()
  const { events, memberFilter, typeFilter, setMemberFilter, toggleType } = useCollabEventStore()
  const listRef = useRef<HTMLDivElement | null>(null)

  const typeLabels = useMemo<Record<CollabEventType, string>>(
    () => ({
      add: t('collabEvents.type.add'),
      delete: t('collabEvents.type.delete'),
      update: t('collabEvents.type.update'),
    }),
    [t],
  )

  const members = useMemo(() => {
    const map = new Map<string, string>()
    events.forEach((event) => {
      if (!map.has(event.actorId)) {
        map.set(event.actorId, event.actorName)
      }
    })
    return Array.from(map.entries())
  }, [events])

  const filtered = useMemo(() => {
    return events.filter((event) => {
      if (memberFilter !== 'all' && event.actorId !== memberFilter) return false
      if (typeFilter && !typeFilter.has(event.type)) return false
      return true
    })
  }, [events, memberFilter, typeFilter])

  const formatTime = useMemo(() => {
    const formatter = new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit',
    })
    return (timestamp: number) => formatter.format(new Date(timestamp))
  }, [locale])

  useEffect(() => {
    const element = listRef.current
    if (!element) return
    if (element.scrollTop < 24) {
      element.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [events.length])

  return (
    <div className="flex h-full flex-col bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="border-b border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className="mb-3 flex items-center gap-2">
          <select
            value={memberFilter}
            onChange={(event) => setMemberFilter(event.target.value)}
            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-900"
          >
            <option value="all">{t('collabEvents.memberFilter.all')}</option>
            {members.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <div className="ml-auto flex items-center gap-2">
            {(['add', 'delete', 'update'] as CollabEventType[]).map((type) => {
              const active = !typeFilter || typeFilter.has(type)

              return (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={cn(
                    'rounded-md border px-2 py-1 text-xs transition-colors',
                    active
                      ? 'border-blue-200 bg-blue-50 text-blue-600 dark:border-blue-800/60 dark:bg-blue-900/40 dark:text-blue-100'
                      : 'border-zinc-200 bg-white text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400',
                  )}
                >
                  {typeLabels[type]}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div ref={listRef} className="flex-1 overflow-auto">
        {filtered.length === 0 && (
          <div className="p-6 text-center text-sm text-zinc-400 dark:text-zinc-500">
            {t('collabEvents.empty')}
          </div>
        )}
        {filtered.map((event) => (
          <EventItem
            key={event.id}
            event={event}
            typeLabels={typeLabels}
            meLabel={t('collabEvents.actor.me')}
            formatTime={formatTime}
          />
        ))}
      </div>
    </div>
  )
}
