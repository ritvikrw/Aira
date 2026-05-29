'use client'

import { Clock } from 'lucide-react'

export function ScheduledList() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-200 flex items-center justify-center mb-4">
        <Clock size={22} className="text-ink-300" />
      </div>
      <p className="text-sm font-medium text-ink-600 mb-1">No scheduled callbacks</p>
      <p className="text-xs text-ink-400">
        Callbacks will appear here when aira schedules follow-ups
      </p>
    </div>
  )
}

export default ScheduledList
