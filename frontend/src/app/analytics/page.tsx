'use client'

import { useEffect, useState, useCallback } from 'react'
import { format, startOfWeek, startOfMonth, subWeeks } from 'date-fns'
import { AppShell } from '@/components/layout/AppShell'
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard'
import { Loader2, RefreshCw, Globe } from 'lucide-react'

const TIMEZONES = [
  { label: 'UTC', value: 'UTC' },
  { label: 'IST (UTC+5:30)', value: 'Asia/Kolkata' },
  { label: 'GST (UTC+4)', value: 'Asia/Dubai' },
  { label: 'CET (UTC+1)', value: 'Europe/Paris' },
  { label: 'GMT (UTC+0)', value: 'Europe/London' },
  { label: 'EST (UTC-5)', value: 'America/New_York' },
  { label: 'PST (UTC-8)', value: 'America/Los_Angeles' },
]

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

const EMPTY_DATA = {
  total_calls: 0, active_calls: 0, calls_today: 0, avg_duration_seconds: 0,
  calls_last_7_days: [], calls_by_hour: [], categories: [],
  status_breakdown: { pending: 0, resolved: 0, urgent: 0 },
  top_topics: [],
}

function toISO(d: Date) { return format(d, 'yyyy-MM-dd') }

const today = new Date()

const PRESETS = [
  { label: 'Today',      start: () => toISO(today),                      end: () => toISO(today) },
  { label: 'Yesterday',  start: () => toISO(new Date(Date.now() - 86400000)), end: () => toISO(new Date(Date.now() - 86400000)) },
  { label: 'This week',  start: () => toISO(startOfWeek(today, { weekStartsOn: 1 })), end: () => toISO(today) },
  { label: 'Last week',  start: () => toISO(startOfWeek(subWeeks(today, 1), { weekStartsOn: 1 })), end: () => toISO(new Date(startOfWeek(today, { weekStartsOn: 1 }).getTime() - 1)) },
  { label: 'This month', start: () => toISO(startOfMonth(today)),         end: () => toISO(today) },
  { label: 'All time',   start: () => '',                                  end: () => '' },
]

export default function AnalyticsPage() {
  const [data, setData] = useState<typeof EMPTY_DATA | null>(null)
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [activePreset, setActivePreset] = useState('All time')
  const [recategorizing, setRecategorizing] = useState(false)
  const [recatResult, setRecatResult] = useState<{ processed: number; failed: number } | null>(null)
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone)

  const fetchData = useCallback((start: string, end: string, tzOverride?: string) => {
    setLoading(true)
    const params = new URLSearchParams()
    if (start) params.set('start_date', start)
    if (end) params.set('end_date', end)
    const activeTz = tzOverride ?? timezone
    if (activeTz) params.set('tz', activeTz)
    fetch(`${API}/calls/analytics/overview?${params}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setData(d || EMPTY_DATA))
      .catch(() => setData(EMPTY_DATA))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchData(startDate, endDate) }, [])  // eslint-disable-line

  const applyPreset = (preset: typeof PRESETS[0]) => {
    const s = preset.start()
    const e = preset.end()
    setStartDate(s)
    setEndDate(e)
    setActivePreset(preset.label)
    fetchData(s, e)
  }

  const applyDates = (s: string, e: string) => {
    setActivePreset('')
    fetchData(s, e)
  }

  const handleRecategorize = async () => {
    setRecategorizing(true)
    setRecatResult(null)
    try {
      const res = await fetch(`${API}/calls/recategorize`, { method: 'POST' })
      const result = await res.json()
      setRecatResult(result)
      // Refresh analytics after recategorisation
      fetchData(startDate, endDate)
    } finally {
      setRecategorizing(false)
    }
  }

  const rangeLabel = activePreset
    ? activePreset
    : startDate && endDate
      ? `${format(new Date(startDate), 'd MMM')} – ${format(new Date(endDate), 'd MMM yyyy')}`
      : startDate
        ? `From ${format(new Date(startDate), 'd MMM yyyy')}`
        : 'All time'

  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h1 className="text-lg font-semibold text-ink-900">Analytics</h1>
              <p className="text-xs text-ink-500 mt-0.5">{format(new Date(), 'EEEE, d MMM yyyy')}</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchData(startDate, endDate)}
                className="flex items-center gap-1.5 text-xs text-ink-500 hover:text-ink-700 px-3 py-1.5 rounded-lg border border-brand-300 hover:bg-brand-50 transition-colors"
              >
                {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                Refresh
              </button>
            </div>
          </div>

          {/* Date controls */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Quick presets */}
            <div className="flex gap-1 flex-wrap">
              {PRESETS.map(p => (
                <button
                  key={p.label}
                  onClick={() => applyPreset(p)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all border ${
                    activePreset === p.label
                      ? 'bg-accent-500 text-white border-accent-500'
                      : 'border-brand-300 text-ink-500 hover:text-ink-700 hover:border-brand-400'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Divider */}
            <div className="h-4 w-px bg-brand-300" />

            {/* Custom range */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                max={endDate || toISO(today)}
                onChange={e => { setStartDate(e.target.value); applyDates(e.target.value, endDate) }}
                className="text-xs px-2 py-1 rounded-lg border border-brand-300 text-ink-700 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
              />
              <span className="text-xs text-ink-400">to</span>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={toISO(today)}
                onChange={e => { setEndDate(e.target.value); applyDates(startDate, e.target.value) }}
                className="text-xs px-2 py-1 rounded-lg border border-brand-300 text-ink-700 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
              />
            </div>

            {/* Timezone selector */}
            <div className="flex items-center gap-1.5 border border-brand-300 rounded-lg px-2 py-1">
              <Globe size={12} className="text-ink-400 shrink-0" />
              <select
                value={timezone}
                onChange={e => { setTimezone(e.target.value); fetchData(startDate, endDate, e.target.value) }}
                className="text-xs text-ink-600 bg-transparent focus:outline-none"
              >
                {TIMEZONES.some(t => t.value === timezone) ? null : (
                  <option value={timezone}>{timezone}</option>
                )}
                {TIMEZONES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Recategorize result toast */}
          {recatResult && (
            <div className="mt-2 text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
              Recategorised {recatResult.processed} call{recatResult.processed !== 1 ? 's' : ''}.
              {recatResult.failed > 0 && ` ${recatResult.failed} failed.`}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {loading && !data ? (
              <div className="flex items-center justify-center py-24 text-ink-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading analytics…
              </div>
            ) : (
              <div className={loading ? 'opacity-50 pointer-events-none transition-opacity' : ''}>
                <AnalyticsDashboard data={data || EMPTY_DATA} rangeLabel={rangeLabel} timezone={timezone} />
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
