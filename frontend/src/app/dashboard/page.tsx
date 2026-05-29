import { AppShell } from '@/components/layout/AppShell'
import { DashboardClient } from '@/components/calls/DashboardClient'
import { format } from 'date-fns'
import { CallData } from '@/components/calls/CallCard'

export const dynamic = 'force-dynamic'

const API = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export default async function DashboardPage() {
  let calls: CallData[] = []
  try {
    const res = await fetch(`${API}/calls/`, { cache: 'no-store' })
    if (res.ok) {
      const raw = await res.json() as Array<{
        session_id: string
        caller_id: string | null
        caller_name: string | null
        status: string
        call_start_time: string
        call_duration_seconds: number | null
        call_category: string | null
        summary_text: string | null
        key_topics: string[]
        action_items: string[]
        room_name: string | null
      }>
      calls = raw.map(c => ({
        ...c,
        call_end_time: null,
      }))
    }
  } catch { /* ignore */ }

  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Call logs</h1>
            <p className="text-xs text-ink-500 mt-0.5">{format(new Date(), 'EEEE, d MMM yyyy')}</p>
          </div>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <DashboardClient calls={calls} agentName="aira" />
        </div>
      </div>
    </AppShell>
  )
}
