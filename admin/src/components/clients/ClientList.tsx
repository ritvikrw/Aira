'use client'

import Link from 'next/link'
import type { Client } from '@/lib/mock'
import { Phone, Calendar, CheckCircle, XCircle, ChevronRight, Users } from 'lucide-react'

const KEY_LABELS: { key: keyof Client; label: string }[] = [
  { key: 'sarvam_key',    label: 'Sarvam'    },
  { key: 'cartesia_key',  label: 'Cartesia'  },
  { key: 'openai_key',    label: 'OpenAI'    },
  { key: 'google_key',    label: 'Google'    },
  { key: 'elevenlabs_key',label: 'ElevenLabs'},
]

function EmptyState() {
  return (
    <div className="text-center py-20 bg-[#111E2E] border border-[#1F3450] rounded-xl">
      <div className="w-12 h-12 bg-[#162335] rounded-full flex items-center justify-center mx-auto mb-4">
        <Users size={20} className="text-[#5E7A95]" />
      </div>
      <p className="text-[#EDF2F7] font-semibold mb-1">No clients yet</p>
      <p className="text-sm text-[#5E7A95] mb-6">Add your first client to get started</p>
      <Link href="/clients/new"
        className="bg-[#C4621A] hover:bg-[#E06B28] text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors">
        Add first client
      </Link>
    </div>
  )
}

export function ClientList({ clients }: { clients: Client[] }) {
  if (!clients.length) return <EmptyState />

  return (
    <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#1F3450]">
            {['Client', 'Email', 'API Keys', 'Calls today', 'Active now', 'Status', ''].map(h => (
              <th key={h} className="text-left text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] px-5 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {clients.map((c, i) => (
            <tr key={c.id}
              className={`hover:bg-[#162335] transition-colors ${i < clients.length - 1 ? 'border-b border-[#1F3450]/60' : ''}`}>
              <td className="px-5 py-4">
                <div className="font-semibold text-sm text-[#EDF2F7]">{c.name}</div>
                <code className="text-[10px] text-[#C4621A] bg-[#162335] border border-[#1F3450] px-1.5 py-0.5 rounded mt-1 inline-block">
                  {c.slug}
                </code>
              </td>
              <td className="px-5 py-4 text-sm text-[#5E7A95]">{c.email}</td>
              <td className="px-5 py-4">
                <div className="flex gap-1 flex-wrap">
                  {KEY_LABELS.map(({ key, label }) => (
                    <span key={key} className={`text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide border ${
                      c[key]
                        ? 'bg-[#00C9A7]/10 border-[#00C9A7]/20 text-[#00C9A7]'
                        : 'bg-[#1F3450]/40 border-[#1F3450] text-[#2A4A6E]'
                    }`}>
                      {label}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-5 py-4">
                <div className="flex items-center gap-1.5 text-sm text-[#EDF2F7] font-mono font-semibold">
                  <Phone size={11} className="text-[#5E7A95]" />
                  {c.calls_today}
                </div>
              </td>
              <td className="px-5 py-4">
                {c.active_calls > 0 ? (
                  <span className="flex items-center gap-1.5 text-sm font-mono font-semibold text-[#2DD4A7]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2DD4A7] animate-pulse inline-block" />
                    {c.active_calls}
                  </span>
                ) : (
                  <span className="text-sm text-[#5E7A95] font-mono">0</span>
                )}
              </td>
              <td className="px-5 py-4">
                {c.is_active ? (
                  <span className="flex items-center gap-1 text-xs text-[#2DD4A7]"><CheckCircle size={12} />Active</span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-[#FF5F6D]"><XCircle size={12} />Inactive</span>
                )}
              </td>
              <td className="px-5 py-4 text-xs text-[#5E7A95]">
                <div className="flex items-center gap-1.5">
                  <Calendar size={11} />
                  {new Date(c.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </div>
              </td>
              <td className="px-5 py-4">
                <Link href={`/clients/${c.id}`} className="text-[#5E7A95] hover:text-[#C4621A] transition-colors">
                  <ChevronRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
