'use client'

import { useState, useEffect, useCallback } from 'react'
import { ChevronDown, ChevronUp, Play, CalendarPlus, Radio, User, RefreshCw } from 'lucide-react'

const CATEGORY_STYLES: Record<string, string> = {
  'Product Enquiry':       'bg-blue-50 text-blue-700',
  'Support Request':       'bg-purple-50 text-purple-700',
  'Billing & Pricing':     'bg-green-50 text-green-700',
  'Appointment / Booking': 'bg-teal-50 text-teal-700',
  'General Information':   'bg-brand-100 text-ink-600',
  'Complaint':             'bg-red-50 text-red-700',
  'Other':                 'bg-brand-100 text-ink-500',
}
import { format } from 'date-fns'
import { Button } from '@/components/ui/Button'
import { CallData } from './CallCard'
import { formatDuration, formatPhone } from '@/lib/utils'
import { translateToEnglish } from '@/lib/translate'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Transcript {
  id: number
  speaker: string
  message: string
  created_at: string
}

interface DetailData {
  summary_text?: string | null
  call_category?: string | null
  key_topics?: string[]
  action_items?: string[]
  call_end_time?: string | null
  room_name?: string | null
  caller_name?: string | null
}

interface CallDetailProps {
  call: CallData | null
  agentName?: string
}

export function CallDetail({ call, agentName = 'aira' }: CallDetailProps) {
  const [transcriptOpen, setTranscriptOpen] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)
  const [detail, setDetail] = useState<DetailData | null>(null)
  const [rawTranscripts, setRawTranscripts] = useState<Transcript[]>([])
  const [displayTranscripts, setDisplayTranscripts] = useState<Transcript[]>([])
  const [transcriptsLoading, setTranscriptsLoading] = useState(false)
  const [translatingTranscripts, setTranslatingTranscripts] = useState(false)
  const [regenerating, setRegenerating] = useState(false)

  const fetchDetail = useCallback((sessionId: string) => {
    fetch(`${API}/calls/${sessionId}`)
      .then(r => r.json())
      .then((d: {
        summary?: { summary_text: string; call_category?: string; key_topics: string[]; action_items: string[] } | null
        call_end_time?: string | null
        room_name?: string | null
        caller_name?: string | null
      }) => {
        setDetail({
          summary_text: d.summary?.summary_text ?? null,
          call_category: d.summary?.call_category ?? null,
          key_topics: d.summary?.key_topics ?? [],
          action_items: d.summary?.action_items ?? [],
          call_end_time: d.call_end_time ?? null,
          room_name: d.room_name ?? null,
          caller_name: d.caller_name ?? null,
        })
      })
      .catch(() => setDetail({ summary_text: null, call_category: null, key_topics: [], action_items: [] }))
  }, [])

  useEffect(() => {
    if (!call) { setDetail(null); setRawTranscripts([]); setDisplayTranscripts([]); return }
    setDetail(null)
    setRawTranscripts([])
    setDisplayTranscripts([])
    setTranscriptOpen(false)
    fetchDetail(call.session_id)
  }, [call?.session_id, fetchDetail])

  // Re-apply translation whenever raw transcripts or the toggle changes
  useEffect(() => {
    if (!rawTranscripts.length) { setDisplayTranscripts([]); return }
    if (showOriginal) {
      setDisplayTranscripts(rawTranscripts)
      return
    }
    setTranslatingTranscripts(true)
    translateToEnglish(rawTranscripts.map(t => t.message))
      .then(translated => {
        setDisplayTranscripts(rawTranscripts.map((t, i) => ({ ...t, message: translated[i] ?? t.message })))
      })
      .finally(() => setTranslatingTranscripts(false))
  }, [rawTranscripts, showOriginal])

  const handleRegenerate = async () => {
    if (!call) return
    setRegenerating(true)
    try {
      await fetch(`${API}/calls/${call.session_id}/summarize`, { method: 'POST' })
      fetchDetail(call.session_id)
    } catch {
    } finally {
      setRegenerating(false)
    }
  }

  const loadTranscripts = () => {
    if (!call) return
    if (rawTranscripts.length > 0) { setTranscriptOpen(o => !o); return }
    setTranscriptOpen(true)
    setTranscriptsLoading(true)
    fetch(`${API}/transcripts/${call.session_id}`)
      .then(r => r.json())
      .then((data: Transcript[]) => setRawTranscripts(data))
      .catch(() => {})
      .finally(() => setTranscriptsLoading(false))
  }

  if (!call) {
    return (
      <div className="flex-1 bg-brand-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-brand-200 flex items-center justify-center mx-auto mb-4">
            <Play size={24} className="text-ink-300" />
          </div>
          <p className="text-ink-500 text-sm">Select a call to view details</p>
        </div>
      </div>
    )
  }

  const startTime = new Date(call.call_start_time)
  const now = new Date()
  const isToday = startTime.toDateString() === now.toDateString()
  const dateStr = isToday ? 'Today' : format(startTime, 'd MMM')
  const timeStr = format(startTime, 'h:mm a')
  const durationStr = call.call_duration_seconds ? formatDuration(call.call_duration_seconds) : '--'
  const isLive = call.status === 'active'
  const category = detail?.call_category || call.call_category || 'Other'
  const categoryStyle = CATEGORY_STYLES[category] || 'bg-brand-100 text-ink-500'
  const tags = detail?.key_topics || []
  const pendingAction = detail?.action_items?.[0] ?? null
  const callerName = detail?.caller_name || call.caller_name
  const looksLikePhone = call.caller_id && /^[+\d\s\-()]{6,}$/.test(call.caller_id)
  const phoneDisplay = call.caller_phone && call.caller_phone !== '+00 00000 00000' ? call.caller_phone : (looksLikePhone ? call.caller_id : null)

  return (
    <div className="flex-1 bg-brand-50 overflow-y-auto">
      <div className="p-6 max-w-2xl">
        {/* Header */}
        <div className="flex justify-between items-start mb-5">
          <div>
            <h1 className="text-3xl font-semibold text-ink-900 tracking-tight flex items-center gap-2">
              {callerName ? (
                <><User size={22} className="text-accent-500" />{callerName}</>
              ) : phoneDisplay ? (
                formatPhone(phoneDisplay)
              ) : (
                <span className="text-ink-400 font-normal">Unknown caller</span>
              )}
            </h1>
            {callerName && phoneDisplay && (
              <p className="text-sm font-mono text-ink-500 mt-0.5">{phoneDisplay}</p>
            )}
            <p className="text-sm text-ink-500 mt-1">
              {dateStr} · {timeStr} · {durationStr}
            </p>
            <div className="mt-2 flex items-center gap-2">
              {isLive ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-600">
                  <Radio size={10} className="animate-pulse" /> Live
                </span>
              ) : (
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${categoryStyle}`}>
                  {category}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2 ml-4">
            <Button variant="outline" size="sm" disabled>
              <Play size={13} />
              Play
            </Button>
            <Button variant="accent" size="sm" disabled title="Scheduled callbacks coming soon">
              <CalendarPlus size={13} />
              Schedule callback
            </Button>
          </div>
        </div>

        {/* Live call banner */}
        {isLive && (
          <div className="bg-red-50 border border-red-200 rounded-xl mb-4 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-red-100">
              <Radio size={13} className="text-red-500 animate-pulse" />
              <span className="text-sm font-semibold text-red-700">Live call in progress</span>
            </div>
            <div className="px-4 py-3">
              <p className="text-xs text-red-400 italic">Call is currently active…</p>
            </div>
          </div>
        )}

        {/* Pending action banner */}
        {pendingAction && (
          <div className="bg-accent-50 border border-accent-200 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-500 flex-shrink-0" />
            <span className="text-sm text-accent-700 italic">
              Action — {pendingAction}
            </span>
          </div>
        )}

        {/* Summary card */}
        <div className="bg-white rounded-xl border border-brand-300 p-5 mb-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400">
              Summary
            </p>
            {detail !== null && !detail.summary_text && !isLive && (
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="flex items-center gap-1.5 text-xs text-accent-600 hover:text-accent-700 disabled:opacity-50 transition-colors"
              >
                <RefreshCw size={11} className={regenerating ? 'animate-spin' : ''} />
                {regenerating ? 'Generating…' : 'Generate summary'}
              </button>
            )}
          </div>
          {detail === null ? (
            <div className="space-y-2">
              <div className="h-3 bg-brand-100 rounded animate-pulse w-full" />
              <div className="h-3 bg-brand-100 rounded animate-pulse w-4/5" />
              <div className="h-3 bg-brand-100 rounded animate-pulse w-2/3" />
            </div>
          ) : detail.summary_text ? (
            <p className="text-sm text-ink-700 leading-relaxed">{detail.summary_text}</p>
          ) : (
            <p className="text-sm text-ink-400 italic">
              {isLive ? 'Summary will be generated when the call ends.' : 'No summary yet — click Generate summary above.'}
            </p>
          )}
          {tags.length > 0 && (
            <div className="flex gap-2 mt-3 flex-wrap">
              {tags.map((tag) => (
                <span key={tag} className="px-3 py-1 rounded-full border border-brand-300 text-xs text-ink-600">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {detail?.action_items && detail.action_items.length > 0 && (
            <div className="mt-4 pt-4 border-t border-brand-100">
              <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400 mb-2">Action items</p>
              <ul className="space-y-1.5">
                {detail.action_items.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-400 mt-1.5 flex-shrink-0" />
                    <span className="text-sm text-ink-700">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-white rounded-xl border border-brand-300 p-5">
            <p className="text-3xl font-semibold text-ink-900">{durationStr}</p>
            <p className="text-xs text-ink-500 mt-1">Call duration</p>
          </div>
          <div className="bg-white rounded-xl border border-brand-300 p-5">
            <p className="text-3xl font-semibold text-ink-900">
              {(detail?.action_items?.length ?? 0) + (detail?.key_topics?.length ?? 0)}
            </p>
            <p className="text-xs text-ink-500 mt-1">Topics & actions</p>
          </div>
        </div>

        {/* Transcript dropdown */}
        <div className="bg-white rounded-xl border border-brand-300 overflow-hidden">
          <div className="px-5 py-4 flex items-center gap-2">
            {/* Clickable title area */}
            <button
              onClick={loadTranscripts}
              className="flex-1 flex items-center gap-2 text-sm font-medium text-ink-700 hover:text-ink-900 transition-colors text-left"
            >
              Transcript
              {rawTranscripts.length > 0 && (
                <span className="text-ink-400 font-normal">({rawTranscripts.length} messages)</span>
              )}
              {translatingTranscripts && (
                <span className="text-[10px] text-ink-400 animate-pulse">Translating…</span>
              )}
            </button>

            {/* EN / Original toggle — only show once transcripts are loaded */}
            {rawTranscripts.length > 0 && (
              <div className="flex items-center rounded-full border border-brand-300 overflow-hidden text-[10px] font-medium flex-shrink-0">
                <button
                  onClick={() => setShowOriginal(false)}
                  className={`px-2.5 py-1 transition-colors ${!showOriginal ? 'bg-accent-500 text-white' : 'text-ink-500 hover:text-ink-700'}`}
                >
                  EN
                </button>
                <button
                  onClick={() => setShowOriginal(true)}
                  className={`px-2.5 py-1 transition-colors border-l border-brand-300 ${showOriginal ? 'bg-accent-500 text-white' : 'text-ink-500 hover:text-ink-700'}`}
                >
                  Original
                </button>
              </div>
            )}

            <button onClick={loadTranscripts} className="text-ink-400 hover:text-ink-600 transition-colors ml-1">
              {transcriptOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>

          {transcriptOpen && (
            <div className="border-t border-brand-100 max-h-96 overflow-y-auto p-4 space-y-3">
              {transcriptsLoading ? (
                <div className="space-y-2 py-4">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-3 bg-brand-100 rounded animate-pulse" style={{ width: `${60 + i * 10}%` }} />
                  ))}
                </div>
              ) : displayTranscripts.length === 0 ? (
                <p className="text-sm text-ink-400 text-center py-6">No transcript recorded.</p>
              ) : (
                (() => {
                  // Merge consecutive messages from the same speaker into one bubble
                  const merged: { speaker: string; messages: string[]; id: number }[] = []
                  for (const t of displayTranscripts) {
                    const last = merged[merged.length - 1]
                    if (last && last.speaker === t.speaker) {
                      last.messages.push(t.message)
                    } else {
                      merged.push({ speaker: t.speaker, messages: [t.message], id: t.id })
                    }
                  }
                  return merged.map(g => (
                    <div key={g.id} className={`flex gap-2 items-end ${g.speaker === 'agent' ? '' : 'flex-row-reverse'}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                        g.speaker === 'agent' ? 'bg-accent-500 text-white' : 'bg-ink-700 text-white'
                      }`}>
                        {g.speaker === 'agent' ? agentName[0].toUpperCase() : 'C'}
                      </div>
                      <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                        g.speaker === 'agent'
                          ? 'bg-accent-500 text-white'
                          : 'bg-ink-800 text-white'
                      }`}>
                        {g.messages.join(' ')}
                      </div>
                    </div>
                  ))
                })()
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CallDetail
