'use client'

import { Badge } from '@/components/ui/Badge'
import { formatDuration, formatPhone } from '@/lib/utils'
import { format } from 'date-fns'
import { User, Radio } from 'lucide-react'

const CATEGORY_STYLES: Record<string, string> = {
  'Product Enquiry':      'bg-blue-50 text-blue-700',
  'Support Request':      'bg-purple-50 text-purple-700',
  'Billing & Pricing':    'bg-green-50 text-green-700',
  'Appointment / Booking':'bg-teal-50 text-teal-700',
  'General Information':  'bg-brand-100 text-ink-600',
  'Complaint':            'bg-red-50 text-red-700',
  'Other':                'bg-brand-100 text-ink-500',
}

export interface CallData {
  session_id: string
  caller_id: string | null
  caller_name?: string | null
  caller_phone?: string | null
  status: string
  call_start_time: string
  call_end_time?: string | null
  call_duration_seconds: number | null
  call_category?: string | null
  summary_text?: string | null
  key_topics?: string[]
  action_items?: string[]
  room_name?: string | null
}

interface CallCardProps {
  call: CallData
  isSelected: boolean
  onClick: () => void
}

export function CallCard({ call, isSelected, onClick }: CallCardProps) {
  const startTime = new Date(call.call_start_time)
  const timeStr = format(startTime, 'h:mm a')
  const durationStr = call.call_duration_seconds ? formatDuration(call.call_duration_seconds) : '--'
  const category = call.call_category || 'Other'
  const categoryStyle = CATEGORY_STYLES[category] || 'bg-brand-100 text-ink-500'
  const looksLikePhone = call.caller_id && /^[+\d\s\-()]{6,}$/.test(call.caller_id)
  const phoneDisplay = call.caller_phone && call.caller_phone !== '+00 00000 00000' ? call.caller_phone : (looksLikePhone ? call.caller_id : null)
  const hasCallbackRequest = call.action_items?.some(a =>
    /call.?back|follow.?up|reach out|get back/i.test(a)
  )

  return (
    <div
      onClick={onClick}
      className={`px-4 py-3 cursor-pointer border-b border-brand-100 transition-colors ${
        isSelected
          ? 'bg-white border-l-2 border-accent-500'
          : 'hover:bg-brand-50 border-l-2 border-transparent'
      }`}
    >
      <div className="flex justify-between items-start mb-0.5">
        <span className="font-semibold text-sm text-ink-900 flex items-center gap-1.5">
          {call.caller_name ? (
            <><User size={12} className="text-accent-500 shrink-0" />{call.caller_name}</>
          ) : phoneDisplay ? (
            formatPhone(phoneDisplay)
          ) : (
            <span className="text-ink-400 font-normal italic">Unknown caller</span>
          )}
        </span>
        <span className="text-xs text-ink-500 ml-2 flex-shrink-0">{timeStr}</span>
      </div>
      {call.caller_name && phoneDisplay && (
        <p className="text-xs text-ink-400 font-mono mb-0.5">{phoneDisplay}</p>
      )}
      <div className="flex justify-between items-center mb-1">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${categoryStyle}`}>
          {category}
        </span>
        <span className="text-xs text-ink-500">{durationStr}</span>
      </div>
      {call.summary_text && (
        <p className="text-xs text-ink-600 mt-1 line-clamp-2 leading-relaxed">
          {call.summary_text}
        </p>
      )}
      <div className="mt-1.5 flex flex-wrap gap-1">
        {call.status === 'active' ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600">
            <Radio size={9} className="animate-pulse" /> Live
          </span>
        ) : null}
        {(call.action_items?.length ?? 0) > 0 && call.status !== 'active' && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
            Action needed
          </span>
        )}
        {hasCallbackRequest && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-700">
            Callback requested
          </span>
        )}
      </div>
    </div>
  )
}

export default CallCard
