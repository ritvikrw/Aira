'use client'

import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import { Phone, Clock, Loader2, ChevronDown, ChevronUp, Sparkles, Tag, CheckSquare, User } from 'lucide-react'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface Transcript { id: number; speaker: string; message: string; created_at: string }
interface Summary { summary_text: string; key_topics: string[]; action_items: string[] }
interface CallFull {
  session_id: string; caller_id: string | null; caller_name: string | null; room_name: string | null
  status: string; call_start_time: string; call_end_time: string | null
  call_duration_seconds: number | null; summary: Summary | null
}

export default function CallDetail({ sessionId }: { sessionId: string }) {
  const [call, setCall] = useState<CallFull | null>(null)
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [loading, setLoading] = useState(true)
  const [summarizing, setSummarizing] = useState(false)
  const [transcriptOpen, setTranscriptOpen] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`${API}/calls/${sessionId}`).then(r => r.json()),
      fetch(`${API}/transcripts/${sessionId}`).then(r => r.json()),
    ]).then(([callData, txData]) => {
      setCall(callData)
      setTranscripts(txData)
    }).finally(() => setLoading(false))
  }, [sessionId])

  const handleSummarize = async () => {
    setSummarizing(true)
    try {
      const res = await fetch(`${API}/calls/${sessionId}/summarize`, { method: 'POST' })
      const data = await res.json()
      setCall(prev => prev ? { ...prev, summary: data } : prev)
    } finally {
      setSummarizing(false)
    }
  }

  if (loading) return (
    <div className="flex-1 flex items-center justify-center text-ink-400">
      <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading call…
    </div>
  )
  if (!call) return null

  const duration = call.call_duration_seconds
    ? `${Math.floor(call.call_duration_seconds / 60)}m ${call.call_duration_seconds % 60}s`
    : '—'

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-brand-200 flex items-center justify-center">
              <Phone className="w-4 h-4 text-ink-500" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink-900 flex items-center gap-1.5">
                {call.caller_name ? (
                  <><User className="w-4 h-4 text-accent-500" />{call.caller_name}</>
                ) : (
                  <span className="text-ink-400 italic font-normal">Unknown caller</span>
                )}
              </h2>
              {call.caller_id && /^[+\d\s\-()]{6,}$/.test(call.caller_id) && (
                <p className="text-xs text-ink-500 font-mono">{call.caller_id}</p>
              )}
              <p className="text-xs text-ink-400">{call.room_name ?? call.session_id}</p>
            </div>
          </div>
        </div>
        <Badge status={call.status === 'active' ? 'active' : 'ended'} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Started', value: format(new Date(call.call_start_time), 'MMM d, h:mm a') },
          { label: 'Duration', value: duration },
          { label: 'Ended', value: call.call_end_time ? format(new Date(call.call_end_time), 'h:mm a') : '—' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-brand-300 p-3">
            <p className="text-xs text-ink-400 uppercase tracking-wide font-semibold">{label}</p>
            <p className="text-sm font-medium text-ink-900 mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-white rounded-xl border border-brand-300 p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-ink-900 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent-500" /> Summary
          </h3>
          {!call.summary && (
            <Button variant="accent" size="sm" onClick={handleSummarize} disabled={summarizing}>
              {summarizing ? <><Loader2 className="w-3 h-3 animate-spin" /> Generating…</> : 'Generate'}
            </Button>
          )}
        </div>
        {call.summary ? (
          <div className="space-y-3">
            <p className="text-sm text-ink-700 leading-relaxed">{call.summary.summary_text}</p>
            {call.summary.key_topics.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                  <Tag className="w-3 h-3" /> Key Topics
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {call.summary.key_topics.map(t => (
                    <span key={t} className="px-2 py-0.5 bg-brand-100 text-ink-600 rounded-full text-xs">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {call.summary.action_items.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                  <CheckSquare className="w-3 h-3" /> Action Items
                </p>
                <ul className="space-y-1">
                  {call.summary.action_items.map(a => (
                    <li key={a} className="text-sm text-ink-700 flex gap-2">
                      <span className="text-accent-500 mt-0.5">•</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink-400">No summary yet. Click Generate to summarise this call.</p>
        )}
      </div>

      {/* Transcript */}
      <div className="bg-white rounded-xl border border-brand-300 overflow-hidden">
        <button
          className="w-full flex items-center justify-between px-5 py-3 border-b border-brand-200"
          onClick={() => setTranscriptOpen(o => !o)}
        >
          <h3 className="text-sm font-semibold text-ink-900">
            Transcript <span className="text-ink-400 font-normal">({transcripts.length} messages)</span>
          </h3>
          {transcriptOpen ? <ChevronUp className="w-4 h-4 text-ink-400" /> : <ChevronDown className="w-4 h-4 text-ink-400" />}
        </button>
        {transcriptOpen && (
          <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
            {transcripts.length === 0 ? (
              <p className="text-sm text-ink-400 text-center py-6">No transcript recorded.</p>
            ) : (
              transcripts.map(t => (
                <div key={t.id} className={`flex gap-2 ${t.speaker === 'agent' ? '' : 'flex-row-reverse'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    t.speaker === 'agent' ? 'bg-accent-100 text-accent-700' : 'bg-brand-300 text-ink-600'
                  }`}>
                    {t.speaker === 'agent' ? 'A' : 'U'}
                  </div>
                  <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                    t.speaker === 'agent'
                      ? 'bg-brand-50 text-ink-800 border border-brand-200'
                      : 'bg-accent-50 text-ink-800 border border-accent-100'
                  }`}>
                    {t.message}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
