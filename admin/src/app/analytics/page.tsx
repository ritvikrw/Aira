'use client'

import { AdminShell } from '@/components/layout/AdminShell'
import { MOCK_CLIENTS, MOCK_CALLS } from '@/lib/mock'

const ALL_CALLS = Object.values(MOCK_CALLS).flat()

const CATEGORIES = ALL_CALLS.reduce<Record<string, number>>((acc, c) => {
  const cat = c.call_category || 'Other'
  acc[cat] = (acc[cat] || 0) + 1
  return acc
}, {})

const CLIENTS_BY_CALLS = [...MOCK_CLIENTS].sort((a, b) => b.total_calls - a.total_calls)

export default function AnalyticsPage() {
  const totalCalls = MOCK_CLIENTS.reduce((s, c) => s + c.total_calls, 0)
  const callsToday = MOCK_CLIENTS.reduce((s, c) => s + c.calls_today, 0)
  const activeCalls = MOCK_CLIENTS.reduce((s, c) => s + c.active_calls, 0)
  const maxCalls = Math.max(...MOCK_CLIENTS.map(c => c.total_calls))

  const catMax = Math.max(...Object.values(CATEGORIES))

  return (
    <AdminShell>
      <div className="p-8">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-[#EDF2F7]">Analytics</h1>
          <p className="text-sm text-[#5E7A95] mt-0.5">Platform-wide overview across all clients</p>
        </div>

        {/* Top stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total clients',    value: MOCK_CLIENTS.length,                    sub: `${MOCK_CLIENTS.filter(c=>c.is_active).length} active` },
            { label: 'Total calls ever', value: totalCalls.toLocaleString(),             sub: 'all clients combined'  },
            { label: 'Calls today',      value: callsToday,                             sub: 'across all clients'    },
            { label: 'Live calls now',   value: activeCalls,                            sub: 'in progress',  live: activeCalls > 0 },
          ].map(s => (
            <div key={s.label} className="bg-[#111E2E] border border-[#1F3450] rounded-xl px-5 py-5">
              <div className="text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-2">{s.label}</div>
              <div className={`text-3xl font-bold font-mono ${s.live ? 'text-[#2DD4A7]' : 'text-[#EDF2F7]'}`}>{s.value}</div>
              <div className="text-xs text-[#5E7A95] mt-1">{s.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Calls by client */}
          <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6">
            <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-5">Calls by client</h2>
            <div className="space-y-4">
              {CLIENTS_BY_CALLS.map(c => (
                <div key={c.id}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-[#EDF2F7] font-medium">{c.name}</span>
                      {!c.is_active && <span className="text-[9px] text-[#5E7A95] uppercase tracking-wide">inactive</span>}
                    </div>
                    <span className="text-sm font-mono text-[#C4D4E3]">{c.total_calls.toLocaleString()}</span>
                  </div>
                  <div className="h-1.5 bg-[#162335] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(c.total_calls / maxCalls) * 100}%`,
                        background: c.is_active ? '#C4621A' : '#2A4A6E',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Calls by category */}
          <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6">
            <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-5">Calls by category</h2>
            <div className="space-y-4">
              {Object.entries(CATEGORIES).sort((a, b) => b[1] - a[1]).map(([cat, count]) => (
                <div key={cat}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-[#EDF2F7]">{cat}</span>
                    <span className="text-sm font-mono text-[#C4D4E3]">{count}</span>
                  </div>
                  <div className="h-1.5 bg-[#162335] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-[#00C9A7]" style={{ width: `${(count / catMax) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Client status table */}
          <div className="col-span-2 bg-[#111E2E] border border-[#1F3450] rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#1F3450]">
              <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95]">Client breakdown</h2>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1F3450]">
                  {['Client', 'Total calls', 'Today', 'Live', 'Keys configured', 'Status'].map(h => (
                    <th key={h} className="text-left text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] px-5 py-2.5">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MOCK_CLIENTS.map((c, i) => {
                  const keysSet = ['sarvam_key','cartesia_key','openai_key','google_key','elevenlabs_key'].filter(k => c[k as keyof typeof c]).length
                  return (
                    <tr key={c.id} className={`hover:bg-[#162335] transition-colors ${i < MOCK_CLIENTS.length - 1 ? 'border-b border-[#1F3450]/40' : ''}`}>
                      <td className="px-5 py-3.5 font-medium text-sm text-[#EDF2F7]">{c.name}</td>
                      <td className="px-5 py-3.5 text-sm font-mono text-[#C4D4E3]">{c.total_calls.toLocaleString()}</td>
                      <td className="px-5 py-3.5 text-sm font-mono text-[#C4D4E3]">{c.calls_today}</td>
                      <td className="px-5 py-3.5">
                        {c.active_calls > 0
                          ? <span className="flex items-center gap-1.5 text-sm text-[#2DD4A7] font-mono"><span className="w-1.5 h-1.5 rounded-full bg-[#2DD4A7] animate-pulse" />{c.active_calls}</span>
                          : <span className="text-sm text-[#5E7A95] font-mono">0</span>
                        }
                      </td>
                      <td className="px-5 py-3.5 text-sm text-[#C4D4E3]">{keysSet} / 5</td>
                      <td className="px-5 py-3.5">
                        {c.is_active
                          ? <span className="text-[9px] font-bold uppercase tracking-wide text-[#2DD4A7] bg-[#2DD4A7]/10 border border-[#2DD4A7]/20 px-2 py-0.5 rounded-full">Active</span>
                          : <span className="text-[9px] font-bold uppercase tracking-wide text-[#FF5F6D] bg-[#FF5F6D]/10 border border-[#FF5F6D]/20 px-2 py-0.5 rounded-full">Inactive</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AdminShell>
  )
}
