'use client'

import { useState, useMemo } from 'react'
import { Phone, Clock, TrendingUp, Sunrise } from 'lucide-react'
import { formatDuration } from '@/lib/utils'

interface CategoryStat { name: string; count: number; percentage: number }
interface HourStat { hour: number; count: number }
interface TopicStat { name: string; count: number }
interface AnalyticsData {
  total_calls: number
  active_calls: number
  calls_today: number
  avg_duration_seconds: number
  calls_last_7_days: { date: string; count: number }[]
  calls_by_hour: HourStat[]
  categories: CategoryStat[]
  top_topics: TopicStat[]
  status_breakdown: { pending: number; resolved: number; urgent: number }
}

interface AnalyticsDashboardProps {
  data: AnalyticsData
  rangeLabel?: string
  timezone?: string
}

const categoryColors = ['bg-accent-500', 'bg-accent-300', 'bg-brand-400', 'bg-brand-500', 'bg-ink-400']

type VolumeView = 'hourly' | 'daily' | 'weekly' | 'monthly'

const VOLUME_TABS: { id: VolumeView; label: string }[] = [
  { id: 'hourly',  label: 'Hourly'  },
  { id: 'daily',   label: 'Daily'   },
  { id: 'weekly',  label: 'Weekly'  },
  { id: 'monthly', label: 'Monthly' },
]

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatDayLabel(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]}`
}

function weekOfMonth(dateStr: string) {
  const d = new Date(dateStr)
  const week = Math.ceil(d.getDate() / 7)
  return `W${week} ${MONTH_NAMES[d.getMonth()]}`
}

function monthLabel(ym: string) {
  const [year, month] = ym.split('-').map(Number)
  return `${MONTH_NAMES[month - 1]} ${String(year).slice(2)}`
}

export function AnalyticsDashboard({ data, rangeLabel = 'All time', timezone }: AnalyticsDashboardProps) {
  const [volumeView, setVolumeView] = useState<VolumeView>('daily')

  const busiestHour = useMemo(() => {
    const hours = data.calls_by_hour ?? []
    if (!hours.length || hours.every(h => h.count === 0)) return '--'
    const peak = hours.reduce((max, h) => h.count > max.count ? h : max, hours[0])
    return peak.count > 0 ? `${String(peak.hour).padStart(2, '0')}:00` : '--'
  }, [data.calls_by_hour])

  const volumeBars = useMemo(() => {
    if (volumeView === 'hourly') {
      return (data.calls_by_hour ?? []).filter(h => h.count > 0).map(h => ({
        label: `${String(h.hour).padStart(2, '0')}:00`,
        shortLabel: `${String(h.hour).padStart(2, '0')}:00`,
        count: h.count,
        title: `${String(h.hour).padStart(2, '0')}:00 — ${h.count} calls`,
      }))
    }

    const daily = data.calls_last_7_days ?? []

    if (volumeView === 'daily') {
      return daily.map(d => ({
        label: formatDayLabel(d.date),
        shortLabel: formatDayLabel(d.date),
        count: d.count,
        title: `${formatDayLabel(d.date)} — ${d.count} calls`,
      }))
    }

    if (volumeView === 'weekly') {
      const map = new Map<string, number>()
      daily.forEach(d => {
        const w = weekOfMonth(d.date)
        map.set(w, (map.get(w) ?? 0) + d.count)
      })
      return Array.from(map.entries()).map(([w, count]) => ({
        label: w, shortLabel: w, count, title: `${w} — ${count} calls`,
      }))
    }

    // monthly
    const map = new Map<string, number>()
    daily.forEach(d => {
      const m = d.date.slice(0, 7)
      map.set(m, (map.get(m) ?? 0) + d.count)
    })
    return Array.from(map.entries()).map(([m, count]) => ({
      label: monthLabel(m), shortLabel: monthLabel(m), count, title: `${monthLabel(m)} — ${count} calls`,
    }))
  }, [volumeView, data])

  const maxBar = Math.max(...volumeBars.map(b => b.count), 1)
  const hasData = volumeBars.some(b => b.count > 0)

  const niceMax = useMemo(() => {
    if (maxBar <= 5) return maxBar
    const mag = Math.pow(10, Math.floor(Math.log10(maxBar)))
    const norm = maxBar / mag
    const nice = norm <= 2 ? 2 : norm <= 5 ? 5 : 10
    return nice * mag
  }, [maxBar])

  const yTicks = useMemo(() => {
    if (niceMax <= 4) {
      return Array.from({ length: niceMax + 1 }, (_, i) => niceMax - i)
    }
    const steps = 4
    return Array.from({ length: steps + 1 }, (_, i) => Math.round((niceMax / steps) * (steps - i)))
  }, [niceMax])

  return (
    <div className="space-y-6">
      {/* Top row: 2×2 stats on left, call volume chart on right */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-6 items-start">
        {/* Left: 2×2 stat cards */}
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            icon={<Phone size={20} className="text-accent-500" />}
            label={`Calls — ${rangeLabel}`}
            value={data.total_calls}
            sub={`${data.calls_today} today`}
          />
          <StatCard
            icon={<Clock size={20} className="text-accent-500" />}
            label="Avg duration"
            value={data.avg_duration_seconds ? formatDuration(data.avg_duration_seconds) : '--'}
            sub="per call"
          />
          <StatCard
            icon={<Sunrise size={20} className="text-amber-500" />}
            label="Busiest hour"
            value={busiestHour}
            sub={timezone ? `${timezone.split('/').pop()?.replace('_', ' ')}` : 'today'}
          />
          <StatCard
            icon={<TrendingUp size={20} className="text-accent-500" />}
            label="Active calls"
            value={data.active_calls}
            sub={data.active_calls > 0 ? 'Live in progress' : 'No active calls'}
          />
        </div>

        {/* Right: Call volume chart */}
        <div className="bg-white rounded-xl border border-brand-300 p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400">
              Call volume — {rangeLabel}
            </p>
            <div className="flex gap-1 bg-brand-100 rounded-lg p-0.5">
              {VOLUME_TABS.map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => setVolumeView(id)}
                  className={`px-2.5 py-1 rounded-md text-[10px] font-medium transition-all ${
                    volumeView === id
                      ? 'bg-accent-500 text-white shadow-sm'
                      : 'text-ink-500 hover:text-ink-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {!hasData ? (
            <p className="text-sm text-ink-400 py-8 text-center">No data for this period</p>
          ) : (
            <div className="flex gap-2">
              <div className="flex flex-col justify-between items-end flex-shrink-0 pr-1" style={{ height: '200px', paddingBottom: '24px' }}>
                {yTicks.map(v => (
                  <span key={v} className="text-[11px] text-ink-400 tabular-nums leading-none">{v}</span>
                ))}
              </div>

              <div className="flex-1 overflow-x-auto">
                <div style={{ minWidth: `${volumeBars.length * 44}px` }}>
                  <div className="relative" style={{ height: '176px' }}>
                    {yTicks.map((v, i) => (
                      <div
                        key={v}
                        className="absolute left-0 right-0 border-t border-brand-100"
                        style={{ top: `${(i / (yTicks.length - 1)) * 100}%` }}
                      />
                    ))}
                    <div className="absolute inset-0 flex items-end gap-1 px-1">
                      {volumeBars.map((bar, i) => {
                        const heightPct = (bar.count / niceMax) * 100
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center justify-end h-full" style={{ minWidth: '32px' }}>
                            {bar.count > 0 && (
                              <span className="text-[11px] font-semibold text-ink-700 mb-1 leading-none">{bar.count}</span>
                            )}
                            <div
                              className="w-full bg-accent-400 rounded-t-sm hover:bg-accent-500 transition-colors cursor-default"
                              style={{ height: `${Math.max(heightPct, bar.count > 0 ? 2 : 0)}%` }}
                              title={bar.title}
                            />
                          </div>
                        )
                      })}
                    </div>
                  </div>
                  <div className="flex gap-1 px-1 mt-1">
                    {volumeBars.map((bar, i) => (
                      <div key={i} className="flex-1 text-center" style={{ minWidth: '32px' }}>
                        <span className="text-[10px] text-ink-400 block truncate">{bar.shortLabel}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>{/* end top row */}

      {/* Bottom row: categories + topics — grow together */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Category breakdown */}
        <div className="bg-white rounded-xl border border-brand-300 p-5">
          <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400 mb-4">
            Calls by category
          </p>
          {!data.categories || data.categories.length === 0 ? (
            <p className="text-sm text-ink-400">No data yet</p>
          ) : (
            <div className="space-y-3">
              {data.categories.map((cat, i) => (
                <div key={cat.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-ink-700 font-medium">{cat.name}</span>
                    <span className="text-ink-500">{cat.count} ({cat.percentage}%)</span>
                  </div>
                  <div className="h-2 bg-brand-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${categoryColors[i % categoryColors.length]}`}
                      style={{ width: `${cat.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top topics tag cloud */}
        <div className="bg-white rounded-xl border border-brand-300 p-5 flex flex-col">
          <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400 mb-4 flex-shrink-0">
            Top topics
          </p>
          <div className="flex-1 relative">
            {!data.top_topics || data.top_topics.length === 0 ? (
              <p className="text-sm text-ink-400">No topics yet</p>
            ) : (
              <TopicsCloud topics={data.top_topics} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps { icon: React.ReactNode; label: string; value: string | number; sub?: string }

function StatCard({ icon, label, value, sub }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-brand-300 p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center">{icon}</div>
        <p className="text-xs text-ink-500 font-medium">{label}</p>
      </div>
      <p className="text-2xl font-semibold text-ink-900">{value}</p>
      {sub && <p className="text-xs text-ink-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function TopicsCloud({ topics }: { topics: TopicStat[] }) {
  const top = topics.slice(0, 30)
  const maxCount = Math.max(...top.map(t => t.count), 1)
  const minCount = Math.min(...top.map(t => t.count), 1)
  const range = maxCount - minCount || 1
  const MIN_SIZE = 10
  const MAX_SIZE = 22

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-2 items-start content-start overflow-hidden absolute inset-0">
      {top.map(t => {
        const normalized = (t.count - minCount) / range
        const size = Math.round(MIN_SIZE + normalized * (MAX_SIZE - MIN_SIZE))
        const opacity = 0.45 + normalized * 0.55
        return (
          <span
            key={t.name}
            title={`${t.count} call${t.count !== 1 ? 's' : ''}`}
            className="cursor-default text-accent-600 hover:text-accent-500 transition-colors font-medium leading-tight px-2 py-0.5 rounded-md bg-accent-50"
            style={{ fontSize: `${size}px`, opacity }}
          >
            {t.name}
          </span>
        )
      })}
    </div>
  )
}

export default AnalyticsDashboard
