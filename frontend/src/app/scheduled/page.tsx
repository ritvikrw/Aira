import { AppShell } from '@/components/layout/AppShell'
import { ScheduledList } from '@/components/scheduled/ScheduledList'
import { format } from 'date-fns'

export const dynamic = 'force-dynamic'

export default function ScheduledPage() {
  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Scheduled callbacks</h1>
            <p className="text-xs text-ink-500 mt-0.5">
              {format(new Date(), 'EEEE, d MMM yyyy')}
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto">
            <ScheduledList />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
