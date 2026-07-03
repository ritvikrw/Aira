'use client'

import { AdminShell } from '@/components/layout/AdminShell'
import { ClientList } from '@/components/clients/ClientList'
import { MOCK_CLIENTS } from '@/lib/mock'
import Link from 'next/link'

export default function ClientsPage() {
  const total = MOCK_CLIENTS.reduce((s, c) => s + c.total_calls, 0)
  const active = MOCK_CLIENTS.reduce((s, c) => s + c.active_calls, 0)

  return (
    <AdminShell>
      <div className="p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-xl font-bold text-[#EDF2F7]">Clients</h1>
            <p className="text-sm text-[#5E7A95] mt-0.5">
              {MOCK_CLIENTS.length} clients · {active} active calls · {total.toLocaleString()} total calls
            </p>
          </div>
          <Link href="/clients/new"
            className="bg-[#C4621A] hover:bg-[#E06B28] text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
            + Add client
          </Link>
        </div>

        {/* Summary stat row */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total clients', value: MOCK_CLIENTS.length },
            { label: 'Active clients', value: MOCK_CLIENTS.filter(c => c.is_active).length },
            { label: 'Live calls now', value: active },
            { label: 'Calls today', value: MOCK_CLIENTS.reduce((s, c) => s + c.calls_today, 0) },
          ].map(s => (
            <div key={s.label} className="bg-[#111E2E] border border-[#1F3450] rounded-xl px-5 py-4">
              <div className="text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-2">{s.label}</div>
              <div className="text-2xl font-bold text-[#EDF2F7] font-mono">{s.value}</div>
            </div>
          ))}
        </div>

        <ClientList clients={MOCK_CLIENTS} />
      </div>
    </AdminShell>
  )
}
