import { formatDistanceToNow, format } from 'date-fns'
import { Phone, Clock, User } from 'lucide-react'
import Badge from '@/components/ui/Badge'

interface Call {
  session_id: string
  caller_id: string | null
  caller_name: string | null
  status: string
  call_start_time: string
  call_duration_seconds: number | null
}

export default function CallCard({
  call,
  selected,
  onClick,
}: {
  call: Call
  selected: boolean
  onClick: () => void
}) {
  const duration = call.call_duration_seconds
    ? `${Math.floor(call.call_duration_seconds / 60)}m ${call.call_duration_seconds % 60}s`
    : '—'

  const displayName = call.caller_name || 'Unknown caller'
  // Show caller_id as phone only if it looks like a phone number (not a UUID)
  const looksLikePhone = call.caller_id && /^[+\d\s\-()]{6,}$/.test(call.caller_id)
  const phone = looksLikePhone ? call.caller_id : null

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-brand-200 transition-all hover:bg-brand-50 ${
        selected ? 'bg-white border-l-2 border-l-accent-500' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-full bg-brand-200 flex items-center justify-center shrink-0">
            <Phone className="w-3.5 h-3.5 text-ink-500" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink-900 truncate flex items-center gap-1">
              {call.caller_name ? (
                <>
                  <User className="w-3 h-3 text-accent-500 shrink-0" />
                  {call.caller_name}
                </>
              ) : (
                <span className="text-ink-400 italic">Unknown caller</span>
              )}
            </p>
            {phone && (
              <p className="text-xs text-ink-500 mt-0.5 font-mono">{phone}</p>
            )}
            <p className="text-xs text-ink-400 mt-0.5">
              {formatDistanceToNow(new Date(call.call_start_time), { addSuffix: true })}
            </p>
          </div>
        </div>
        <Badge status={call.status === 'active' ? 'active' : 'ended'} />
      </div>
      <div className="flex items-center gap-3 mt-2 ml-10">
        <span className="flex items-center gap-1 text-xs text-ink-400">
          <Clock className="w-3 h-3" />
          {duration}
        </span>
        <span className="text-xs text-ink-400">
          {format(new Date(call.call_start_time), 'MMM d, h:mm a')}
        </span>
      </div>
    </button>
  )
}
