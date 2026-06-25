'use client'

import { useEffect, useState, useMemo } from 'react'
import { Phone, Loader2 } from 'lucide-react'
import { startOfDay, subDays, subMonths, isAfter } from 'date-fns'
import CallCard from './CallCard'
import CallDetail from './CallDetail'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Call {
  session_id: string
  caller_id: string | null
  caller_name: string | null
  status: string
  call_start_time: string
  call_duration_seconds: number | null
}

type StatusFilter = 'all' | 'active' | 'ended'
type DateFilter = 'today' | '7d' | '30d' | 'all'

const DATE_OPTIONS: { key: DateFilter; label: string }[] = [
  { key: 'today', label: 'Today' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: 'all', label: 'All time' },
]

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'ended', label: 'Ended' },
]

export default function DashboardClient() {
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [dateFilter, setDateFilter] = useState<DateFilter>('all')

  useEffect(() => {
    fetch(`${API}/calls/`)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(data => { setCalls(data); if (data.length > 0) setSelected(data[0].session_id) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const now = new Date()
    const cutoff: Record<DateFilter, Date | null> = {
      today: startOfDay(now),
      '7d': subDays(now, 7),
      '30d': subMonths(now, 1),
      all: null,
    }
    const since = cutoff[dateFilter]

    return calls.filter(c => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false
      if (since && !isAfter(new Date(c.call_start_time), since)) return false
      return true
    })
  }, [calls, statusFilter, dateFilter])

  return (
    <div className="flex h-full">
      {/* Left: Call list */}
      <div className="w-[340px] shrink-0 border-r border-brand-300 flex flex-col bg-white">
        {/* Status tabs */}
        <div className="px-4 pt-4 pb-2 border-b border-brand-200 space-y-2">
          <div className="flex gap-1 bg-brand-100 rounded-lg p-1">
            {STATUS_TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-all ${
                  statusFilter === key ? 'bg-accent-500 text-white shadow-sm' : 'text-ink-500 hover:text-ink-700'
                }`}
              >
                {label}
                {key !== 'all' && (
                  <span className="ml-1 opacity-70">
                    ({calls.filter(c => c.status === key).length})
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Date filter */}
          <div className="flex gap-1">
            {DATE_OPTIONS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setDateFilter(key)}
                className={`flex-1 text-[10px] py-1 rounded-md font-medium transition-all border ${
                  dateFilter === key
                    ? 'bg-accent-50 border-accent-400 text-accent-700'
                    : 'border-brand-200 text-ink-400 hover:text-ink-600 hover:border-brand-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-ink-400">
              <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading…
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center px-6">
              <Phone className="w-8 h-8 text-brand-400 mb-3" />
              <p className="text-sm text-ink-500">No calls found</p>
              <p className="text-xs text-ink-400 mt-1">Try adjusting the filters above</p>
            </div>
          ) : (
            filtered.map(call => (
              <CallCard
                key={call.session_id}
                call={call}
                selected={selected === call.session_id}
                onClick={() => setSelected(call.session_id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: Call detail */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selected ? (
          <CallDetail sessionId={selected} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8 py-16">
            <Phone className="w-10 h-10 text-brand-400 mb-3" />
            <p className="text-sm text-ink-500">Select a call to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
