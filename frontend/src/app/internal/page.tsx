'use client'

import { useEffect, useState, useCallback } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { format } from 'date-fns'
import { RefreshCw, Loader2, Zap, Type, Mic, Bot, Clock } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface MetricRow {
  session_id: string
  caller_name: string | null
  caller_id: string | null
  call_start_time: string | null
  call_duration_seconds: number | null
  status: string
  llm_prompt_tokens: number
  llm_completion_tokens: number
  llm_total_tokens: number
  llm_ttft_ms: number | null
  llm_requests: number
  tts_provider: string
  tts_characters: number
  tts_ttfb_ms: number | null
  tts_requests: number
  stt_audio_duration_ms: number
  stt_ttft_ms: number | null
  stt_requests: number
}

interface Summary {
  total_calls: number
  avg_llm_ttft_ms: number | null
  avg_tts_ttfb_ms: number | null
  avg_stt_ttft_ms: number | null
  total_llm_tokens: number
  total_tts_characters: number
  total_stt_duration_ms: number
}

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-brand-300 p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center">{icon}</div>
        <p className="text-xs text-ink-500 font-medium">{label}</p>
      </div>
      <p className="text-2xl font-semibold text-ink-900">{value}</p>
      {sub && <p className="text-xs text-ink-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function ms(val: number | null | undefined) {
  if (!val) return '—'
  return val < 1000 ? `${Math.round(val)}ms` : `${(val / 1000).toFixed(1)}s`
}

function LatencyBadge({ val, color }: { val: number | null | undefined; color: string }) {
  if (!val) return <span className="text-ink-300 font-mono">—</span>
  const label = val < 1000 ? `${Math.round(val)}ms` : `${(val / 1000).toFixed(1)}s`
  // colour intensity based on speed: green <500ms, amber <1500ms, red otherwise
  const intensity = val < 500 ? 'text-emerald-600' : val < 1500 ? 'text-amber-600' : 'text-red-500'
  return <span className={`font-mono font-semibold ${intensity}`}>{label}</span>
}

export default function InternalPage() {
  const [rows, setRows] = useState<MetricRow[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [metricsRes, summaryRes] = await Promise.all([
        fetch(`${API}/internal/metrics`),
        fetch(`${API}/internal/metrics/summary`),
      ])
      if (metricsRes.ok) setRows(await metricsRes.json())
      if (summaryRes.ok) setSummary(await summaryRes.json())
    } catch {
      // API unreachable — fail silently, show empty state
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex-shrink-0 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Internal</h1>
            <p className="text-xs text-ink-500 mt-0.5">Token usage · Latency · Per-call breakdown</p>
          </div>
          <button
            onClick={load}
            className="flex items-center gap-1.5 text-xs text-ink-500 hover:text-ink-700 px-3 py-1.5 rounded-lg border border-brand-300 hover:bg-brand-50 transition-colors"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Refresh
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {/* Summary cards */}
          {summary && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard
                icon={<Zap size={18} className="text-purple-500" />}
                label="Avg LLM TTFT"
                value={ms(summary.avg_llm_ttft_ms)}
                sub="Time to first token"
              />
              <StatCard
                icon={<Mic size={18} className="text-amber-500" />}
                label="Avg STT latency"
                value={ms(summary.avg_stt_ttft_ms)}
                sub="Speech recognition time"
              />
              <StatCard
                icon={<Clock size={18} className="text-teal-500" />}
                label="Avg TTS latency"
                value={ms(summary.avg_tts_ttfb_ms)}
                sub="Time to first audio byte"
              />
              <StatCard
                icon={<Bot size={18} className="text-blue-500" />}
                label="Total LLM tokens"
                value={summary.total_llm_tokens.toLocaleString()}
                sub={`across ${summary.total_calls} calls`}
              />
            </div>
          )}

          {/* Metrics table */}
          <div className="bg-white rounded-xl border border-brand-300 overflow-hidden">
            <div className="px-5 py-3 border-b border-brand-100 flex items-center justify-between">
              <p className="text-[10px] font-semibold tracking-widest uppercase text-ink-400">Per-call metrics</p>
              <p className="text-xs text-ink-400">{rows.length} calls</p>
            </div>

            {loading && rows.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-ink-400">
                <Loader2 size={20} className="animate-spin mr-2" /> Loading…
              </div>
            ) : rows.length === 0 ? (
              <p className="text-sm text-ink-400 text-center py-16">No metrics yet — make a call first.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-brand-100 bg-brand-50">
                      <th className="px-4 py-2.5 text-left text-[10px] font-semibold text-ink-400 uppercase tracking-wide">Caller</th>
                      <th className="px-4 py-2.5 text-left text-[10px] font-semibold text-ink-400 uppercase tracking-wide">Time</th>
                      {/* Latency group */}
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-amber-500 uppercase tracking-wide">STT latency</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-purple-500 uppercase tracking-wide">LLM TTFT</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-teal-500 uppercase tracking-wide">TTS latency</th>
                      {/* LLM tokens */}
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-purple-400 uppercase tracking-wide">Prompt tkns</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-purple-400 uppercase tracking-wide">Compl tkns</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-purple-400 uppercase tracking-wide">Total tkns</th>
                      {/* TTS */}
                      <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-teal-400 uppercase tracking-wide">TTS provider</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-teal-400 uppercase tracking-wide">TTS chars</th>
                      {/* STT audio */}
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-amber-400 uppercase tracking-wide">STT audio</th>
                      <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-ink-400 uppercase tracking-wide">Reqs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={r.session_id} className={`border-b border-brand-50 ${i % 2 === 0 ? '' : 'bg-brand-50/40'} hover:bg-brand-50 transition-colors`}>
                        <td className="px-4 py-2.5 font-medium text-ink-800">
                          {r.caller_name || r.caller_id || <span className="text-ink-400 italic">Unknown</span>}
                        </td>
                        <td className="px-4 py-2.5 text-ink-500">
                          {r.call_start_time ? format(new Date(r.call_start_time), 'd MMM, h:mm a') : '—'}
                        </td>
                        {/* Latency trio — colour-coded by speed */}
                        <td className="px-3 py-2.5 text-right"><LatencyBadge val={r.stt_ttft_ms} color="amber" /></td>
                        <td className="px-3 py-2.5 text-right"><LatencyBadge val={r.llm_ttft_ms} color="purple" /></td>
                        <td className="px-3 py-2.5 text-right"><LatencyBadge val={r.tts_ttfb_ms} color="teal" /></td>
                        {/* Token counts */}
                        <td className="px-3 py-2.5 text-right font-mono text-purple-500">{r.llm_prompt_tokens.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono text-purple-500">{r.llm_completion_tokens.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono font-semibold text-purple-700">{r.llm_total_tokens.toLocaleString()}</td>
                        {/* TTS */}
                        <td className="px-3 py-2.5 text-left text-teal-700 font-medium max-w-[160px] truncate">{r.tts_provider}</td>
                        <td className="px-3 py-2.5 text-right font-mono text-teal-600">{r.tts_characters.toLocaleString()}</td>
                        {/* STT audio */}
                        <td className="px-3 py-2.5 text-right font-mono text-amber-600">{ms(r.stt_audio_duration_ms)}</td>
                        <td className="px-3 py-2.5 text-right font-mono text-ink-500">{r.llm_requests}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Latency legend */}
          <div className="mt-3 flex items-center gap-4 text-[10px] text-ink-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> &lt; 500ms — fast</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> 500ms–1.5s — acceptable</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> &gt; 1.5s — slow</span>
            <span className="ml-auto">STT latency = Sarvam API response time · LLM TTFT = first token · TTS latency = first audio byte</span>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
