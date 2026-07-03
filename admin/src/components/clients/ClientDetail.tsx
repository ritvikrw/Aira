'use client'

import { useState } from 'react'
import type { Client, CallLog } from '@/lib/mock'
import { Clock, XCircle, Eye, EyeOff, Trash2, ChevronLeft, Mail, KeyRound } from 'lucide-react'
import Link from 'next/link'

const KEY_FIELDS: { key: keyof Client; label: string }[] = [
  { key: 'sarvam_key',     label: 'Sarvam'     },
  { key: 'cartesia_key',   label: 'Cartesia'   },
  { key: 'openai_key',     label: 'OpenAI'     },
  { key: 'google_key',     label: 'Google'     },
  { key: 'elevenlabs_key', label: 'ElevenLabs' },
]

const CATEGORY_COLORS: Record<string, string> = {
  Sales:       'bg-[#4DA6FF]/10 border-[#4DA6FF]/20 text-[#4DA6FF]',
  Support:     'bg-[#C4621A]/10 border-[#C4621A]/20 text-[#C4621A]',
  Enquiry:     'bg-[#F5A623]/10 border-[#F5A623]/20 text-[#F5A623]',
  Appointment: 'bg-[#00C9A7]/10 border-[#00C9A7]/20 text-[#00C9A7]',
  Order:       'bg-[#A78BFA]/10 border-[#A78BFA]/20 text-[#A78BFA]',
  Refund:      'bg-[#FF5F6D]/10 border-[#FF5F6D]/20 text-[#FF5F6D]',
  Other:       'bg-[#1F3450] border-[#1F3450] text-[#5E7A95]',
}

function KeyRow({ label, value }: { label: string; value: string | null }) {
  const [show, setShow] = useState(false)
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value || '')
  const [copied, setCopied] = useState(false)

  const masked = val ? val.slice(0, 6) + '••••••••' + val.slice(-4) : ''

  function copy() {
    if (!val) return
    navigator.clipboard.writeText(val)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[#1F3450]/50 last:border-0">
      <div className="w-24 text-[10px] font-semibold uppercase tracking-wide text-[#5E7A95] flex-shrink-0">{label}</div>
      {editing ? (
        <div className="flex gap-2 flex-1">
          <input value={val} onChange={e => setVal(e.target.value)} autoFocus
            className="flex-1 bg-[#0B1622] border border-[#C4621A] rounded px-2.5 py-1.5 text-xs font-mono text-[#EDF2F7] outline-none" />
          <button onClick={() => setEditing(false)}
            className="text-xs bg-[#C4621A] hover:bg-[#E06B28] text-white px-3 py-1 rounded font-semibold">Save</button>
          <button onClick={() => { setVal(value || ''); setEditing(false) }}
            className="text-xs text-[#5E7A95] hover:text-[#C4D4E3] px-2">Cancel</button>
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {val ? (
            <code className="text-xs font-mono text-[#C4D4E3] flex-1 truncate">{show ? val : masked}</code>
          ) : (
            <span className="text-xs text-[#2A4A6E] italic flex-1">Not set</span>
          )}
          {val && (
            <>
              <button onClick={() => setShow(s => !s)} className="text-[#5E7A95] hover:text-[#C4D4E3] flex-shrink-0">
                {show ? <EyeOff size={12} /> : <Eye size={12} />}
              </button>
              <button onClick={copy} className="text-[#5E7A95] hover:text-[#C4621A] flex-shrink-0">
                <Copy size={11} />
              </button>
              {copied && <span className="text-[10px] text-[#2DD4A7]">Copied</span>}
            </>
          )}
          <button onClick={() => setEditing(true)}
            className="text-[9px] font-semibold uppercase tracking-wide text-[#C4621A] hover:text-[#E06B28] flex-shrink-0">
            {val ? 'Edit' : 'Add'}
          </button>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="bg-[#162335] border border-[#1F3450] rounded-lg px-4 py-4">
      <div className="text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-2">{label}</div>
      <div className={`text-2xl font-bold font-mono ${accent ? 'text-[#2DD4A7]' : 'text-[#EDF2F7]'}`}>{value}</div>
    </div>
  )
}

export function ClientDetail({ client, calls }: { client: Client; calls: CallLog[] }) {
  const [active, setActive] = useState(client.is_active)
  const [email, setEmail] = useState(client.email)
  const [editingEmail, setEditingEmail] = useState(false)
  const [pwReset, setPwReset] = useState(false)

  const ended = calls.filter(c => c.call_duration_seconds)
  const avgDur = ended.length ? Math.round(ended.reduce((s, c) => s + (c.call_duration_seconds || 0), 0) / ended.length) : 0

  function sendPasswordReset() {
    setPwReset(true)
    setTimeout(() => setPwReset(false), 2500)
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <Link href="/clients" className="flex items-center gap-1 text-xs text-[#5E7A95] hover:text-[#C4D4E3] transition-colors mb-3">
            <ChevronLeft size={12} /> Clients
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-[#EDF2F7]">{client.name}</h1>
            <code className="text-xs bg-[#162335] border border-[#1F3450] px-2 py-0.5 rounded text-[#C4621A]">{client.slug}</code>
            <span className={`text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full border ${
              active
                ? 'text-[#2DD4A7] bg-[#2DD4A7]/10 border-[#2DD4A7]/20'
                : 'text-[#FF5F6D] bg-[#FF5F6D]/10 border-[#FF5F6D]/20'
            }`}>{active ? 'Active' : 'Inactive'}</span>
          </div>
          <p className="text-xs text-[#5E7A95] mt-1">
            Added {new Date(client.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setActive(a => !a)}
            className="text-xs border border-[#1F3450] hover:border-[#2A4A6E] text-[#5E7A95] hover:text-[#C4D4E3] px-3 py-1.5 rounded-lg transition-colors">
            {active ? 'Deactivate' : 'Activate'}
          </button>
          <button onClick={() => confirm('Delete this client?')}
            className="flex items-center gap-1.5 text-xs border border-[#FF5F6D]/30 hover:border-[#FF5F6D] text-[#FF5F6D] px-3 py-1.5 rounded-lg transition-colors">
            <Trash2 size={11} /> Delete
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Stat label="Total calls" value={client.total_calls.toLocaleString()} />
        <Stat label="Calls today" value={client.calls_today} />
        <Stat label="Active now" value={client.active_calls} accent={client.active_calls > 0} />
        <Stat label="Avg duration" value={avgDur ? `${avgDur}s` : '—'} />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Login credentials */}
        <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6">
          <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-1">Dashboard login</h2>
          <p className="text-xs text-[#5E7A95] mb-4">Client uses these credentials to access their dashboard.</p>

          {/* Email */}
          <div className="mb-4">
            <label className="block text-[10px] font-semibold uppercase tracking-wide text-[#5E7A95] mb-1.5">
              <Mail size={10} className="inline mr-1" />Email
            </label>
            {editingEmail ? (
              <div className="flex gap-2">
                <input value={email} onChange={e => setEmail(e.target.value)} autoFocus
                  className="flex-1 bg-[#0B1622] border border-[#C4621A] rounded-lg px-3 py-2 text-sm text-[#EDF2F7] outline-none" />
                <button onClick={() => setEditingEmail(false)}
                  className="text-xs bg-[#C4621A] hover:bg-[#E06B28] text-white px-3 rounded-lg font-semibold">Save</button>
                <button onClick={() => { setEmail(client.email); setEditingEmail(false) }}
                  className="text-xs text-[#5E7A95] hover:text-[#C4D4E3] px-2">Cancel</button>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-[#0B1622] border border-[#1F3450] rounded-lg px-3 py-2">
                <span className="text-sm text-[#C4D4E3] flex-1">{email}</span>
                <button onClick={() => setEditingEmail(true)}
                  className="text-[9px] font-semibold uppercase tracking-wide text-[#C4621A] hover:text-[#E06B28]">Edit</button>
              </div>
            )}
          </div>

          {/* Password reset */}
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wide text-[#5E7A95] mb-1.5">
              <KeyRound size={10} className="inline mr-1" />Password
            </label>
            <button onClick={sendPasswordReset}
              className="flex items-center gap-2 text-sm border border-[#1F3450] hover:border-[#2A4A6E] text-[#5E7A95] hover:text-[#C4D4E3] px-3 py-2 rounded-lg transition-colors w-full">
              Send password reset email
            </button>
            {pwReset && <p className="text-xs text-[#2DD4A7] mt-2">Reset email sent to {email}</p>}
          </div>
        </div>

        {/* Client API keys */}
        <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6">
          <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-1">Client API keys</h2>
          <p className="text-xs text-[#5E7A95] mb-3">Keys used for this client's voice calls.</p>
          {KEY_FIELDS.map(({ key, label }) => (
            <KeyRow key={key} label={label} value={client[key] as string | null} />
          ))}
        </div>
      </div>

      {/* Call log */}
      <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#1F3450] flex items-center justify-between">
          <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95]">Recent calls</h2>
          <span className="text-xs text-[#5E7A95]">{calls.length} shown</span>
        </div>

        {calls.length === 0 ? (
          <div className="text-center py-12 text-sm text-[#5E7A95]">No calls yet for this client.</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#1F3450]">
                {['Caller', 'Status', 'Duration', 'Category', 'Time'].map(h => (
                  <th key={h} className="text-left text-[9px] font-semibold tracking-widest uppercase text-[#5E7A95] px-5 py-2.5">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {calls.map((call, i) => (
                <tr key={call.session_id}
                  className={`hover:bg-[#162335] transition-colors ${i < calls.length - 1 ? 'border-b border-[#1F3450]/40' : ''}`}>
                  <td className="px-5 py-3.5">
                    <div className="text-sm text-[#EDF2F7]">{call.caller_name || '—'}</div>
                    <div className="text-[10px] text-[#5E7A95]">{call.caller_phone}</div>
                  </td>
                  <td className="px-5 py-3.5">
                    {call.status === 'active' ? (
                      <span className="flex items-center gap-1.5 text-xs text-[#2DD4A7]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#2DD4A7] animate-pulse" />
                        Live
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-[#5E7A95]">
                        <XCircle size={11} /> Ended
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="flex items-center gap-1 text-xs text-[#C4D4E3]">
                      <Clock size={11} className="text-[#5E7A95]" />
                      {call.call_duration_seconds ? `${call.call_duration_seconds}s` : '—'}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    {call.call_category ? (
                      <span className={`text-[9px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wide ${CATEGORY_COLORS[call.call_category] || CATEGORY_COLORS.Other}`}>
                        {call.call_category}
                      </span>
                    ) : <span className="text-xs text-[#5E7A95]">—</span>}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-[#5E7A95]">
                    {new Date(call.call_start_time).toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
