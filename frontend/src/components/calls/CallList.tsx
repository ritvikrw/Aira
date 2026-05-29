'use client'

import { useState, useMemo } from 'react'
import { CallCard, CallData } from './CallCard'
import { PhoneIncoming, ChevronDown, CalendarDays } from 'lucide-react'
import { format, subDays, startOfWeek } from 'date-fns'

const CATEGORIES = [
  'Product Enquiry',
  'Support Request',
  'Billing & Pricing',
  'Appointment / Booking',
  'General Information',
  'Complaint',
  'Other',
]

const toISO = (d: Date) => format(d, 'yyyy-MM-dd')

type QuickFilter = 'today' | 'yesterday' | 'week' | 'all' | 'custom'

const QUICK_FILTERS: { id: QuickFilter; label: string }[] = [
  { id: 'today',     label: 'Today' },
  { id: 'yesterday', label: 'Yesterday' },
  { id: 'week',      label: 'This week' },
  { id: 'all',       label: 'All' },
]

interface CallListProps {
  calls: CallData[]
  selectedCallId?: string
  onSelectCall?: (id: string) => void
}

export function CallList({ calls, selectedCallId, onSelectCall }: CallListProps) {
  const [category, setCategory] = useState('')
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('today')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')

  const clearSelection = () => onSelectCall?.('')

  const getDateRange = (q: QuickFilter): { from: string; to: string } => {
    const now = new Date()
    if (q === 'today')     return { from: toISO(now), to: toISO(now) }
    if (q === 'yesterday') return { from: toISO(subDays(now, 1)), to: toISO(subDays(now, 1)) }
    if (q === 'week')      return { from: toISO(startOfWeek(now, { weekStartsOn: 1 })), to: toISO(now) }
    if (q === 'custom')    return { from: customFrom, to: customTo }
    return { from: '', to: '' }
  }

  const handleCustomDate = (from: string, to: string) => {
    setCustomFrom(from); setCustomTo(to)
    setQuickFilter('custom'); clearSelection()
  }

  const filteredCalls = useMemo(() => {
    const { from, to } = getDateRange(quickFilter)
    return calls.filter(c => {
      if (category && c.call_category !== category) return false
      const t = new Date(c.call_start_time)
      if (from && t < new Date(from)) return false
      if (to && t > new Date(to + 'T23:59:59')) return false
      return true
    })
  }, [calls, category, quickFilter, customFrom, customTo])

  return (
    <div className="w-[350px] flex-shrink-0 bg-white border-r border-brand-300 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-brand-300 space-y-2">
        {/* Title */}
        <div className="flex items-center gap-2">
          <PhoneIncoming size={15} className="text-ink-400" />
          <span className="text-xs font-semibold tracking-widest uppercase text-ink-400">Inbound Calls</span>
          <span className="ml-auto inline-flex items-center justify-center w-5 h-5 rounded-full bg-brand-200 text-ink-600 text-[10px] font-semibold">
            {filteredCalls.length}
          </span>
        </div>

        {/* Row 1: quick date filters */}
        <div className="flex items-center gap-1">
          {QUICK_FILTERS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => { setQuickFilter(id); clearSelection() }}
              className={`flex-1 py-1.5 text-[10px] font-medium rounded-lg border transition-all whitespace-nowrap ${
                quickFilter === id
                  ? 'bg-accent-500 text-white border-accent-500'
                  : 'border-brand-200 text-ink-500 hover:border-accent-300 hover:text-ink-700 bg-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Row 2: category + date range in one line */}
        <div className="flex items-center gap-1.5">
          <div className="relative flex-1 min-w-0">
            <select
              value={category}
              onChange={e => { setCategory(e.target.value); clearSelection() }}
              className="w-full text-[10px] px-2 py-1.5 rounded-lg border border-brand-200 text-ink-600 bg-white focus:outline-none focus:border-accent-400 appearance-none pr-5 cursor-pointer"
            >
              <option value="">Category</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <ChevronDown size={10} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-ink-400 pointer-events-none" />
          </div>
          <div className={`flex items-center gap-1 rounded-lg px-2 py-1.5 border min-w-0 ${quickFilter === 'custom' ? 'border-accent-400 bg-accent-50' : 'border-brand-200 bg-brand-50'}`}>
            <CalendarDays size={10} className="text-ink-400 shrink-0" />
            <input
              type="date"
              value={quickFilter === 'custom' ? customFrom : ''}
              onChange={e => handleCustomDate(e.target.value, customTo)}
              className="w-16 text-[10px] bg-transparent text-ink-600 focus:outline-none cursor-pointer"
            />
            <span className="text-[10px] text-ink-300 shrink-0">–</span>
            <input
              type="date"
              value={quickFilter === 'custom' ? customTo : ''}
              onChange={e => handleCustomDate(customFrom, e.target.value)}
              className="w-16 text-[10px] bg-transparent text-ink-600 focus:outline-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Call list */}
      <div className="flex-1 overflow-y-auto">
        {filteredCalls.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <div className="w-10 h-10 rounded-full bg-brand-100 flex items-center justify-center mb-3">
              <PhoneIncoming size={18} className="text-ink-300" />
            </div>
            <p className="text-sm text-ink-500">No calls found</p>
            <p className="text-xs text-ink-400 mt-1">Try adjusting the filters</p>
          </div>
        ) : (
          filteredCalls.map((call) => (
            <CallCard
              key={call.session_id}
              call={call}
              isSelected={call.session_id === selectedCallId}
              onClick={() => onSelectCall?.(call.session_id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default CallList
