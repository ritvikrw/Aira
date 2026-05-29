'use client'

import { AppShell } from '@/components/layout/AppShell'
import { useEffect, useState } from 'react'
import { CheckCircle, Loader2, Clock, UserX, ShieldOff, StickyNote } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// Character limits calculated so total system prompt stays under ~500 tokens
const LIMITS = {
  business_hours: 150,
  human_escalation: 300,
  topics_to_avoid: 200,
  custom_instructions: 400,
} as const

type FieldKey = keyof typeof LIMITS

interface Fields {
  business_hours: string
  human_escalation: string
  topics_to_avoid: string
  custom_instructions: string
}

const DEFAULTS: Fields = {
  business_hours: '',
  human_escalation: '',
  topics_to_avoid: '',
  custom_instructions: '',
}

function CharCount({ value, max }: { value: string; max: number }) {
  const pct = value.length / max
  if (pct === 0) return null
  const label = pct > 0.9 ? 'Too long' : pct > 0.7 ? 'Getting long' : 'Good'
  const color = pct > 0.9 ? 'text-red-500' : pct > 0.7 ? 'text-amber-500' : 'text-green-600'
  return <span className={`text-xs font-medium ${color}`}>{label}</span>
}

function Field({
  fieldKey,
  icon,
  label,
  hint,
  placeholder,
  value,
  onChange,
  multiline = false,
}: {
  fieldKey: FieldKey
  icon: React.ReactNode
  label: string
  hint: string
  placeholder: string
  value: string
  onChange: (v: string) => void
  multiline?: boolean
}) {
  const max = LIMITS[fieldKey]
  const pct = value.length / max

  return (
    <div className="bg-white rounded-xl border border-brand-300 p-5">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center flex-shrink-0 mt-0.5">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-ink-900">{label}</p>
          <p className="text-xs text-ink-400 mt-0.5">{hint}</p>
        </div>
      </div>
      {multiline ? (
        <textarea
          rows={3}
          maxLength={max}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full text-sm border border-brand-300 rounded-lg px-3 py-2 text-ink-800 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent resize-none"
        />
      ) : (
        <input
          type="text"
          maxLength={max}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full text-sm border border-brand-300 rounded-lg px-3 py-2 text-ink-800 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent"
        />
      )}
      <div className="flex items-center justify-between mt-1.5">
        {/* progress bar */}
        <div className="flex-1 h-0.5 bg-brand-100 rounded-full mr-3">
          <div
            className={`h-0.5 rounded-full transition-all ${pct > 0.9 ? 'bg-red-400' : pct > 0.7 ? 'bg-amber-400' : 'bg-accent-500'}`}
            style={{ width: `${Math.min(pct * 100, 100)}%` }}
          />
        </div>
        <CharCount value={value} max={max} />
      </div>
    </div>
  )
}

function PromptHealth({ fields }: { fields: Fields }) {
  const instrChars = Object.values(fields).join('').length
  const pct = instrChars / 1050
  const label = pct > 0.95 ? 'Near limit' : pct > 0.8 ? 'Getting full' : 'Healthy'
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
      pct > 0.95 ? 'bg-red-50 text-red-600' :
      pct > 0.8  ? 'bg-amber-50 text-amber-600' :
                   'bg-green-50 text-green-600'
    }`}>{label}</span>
  )
}

export default function InstructionsPage() {
  const [fields, setFields] = useState<Fields>(DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch(`${API}/settings`)
      .then(r => r.json())
      .then((s: Record<string, string>) => {
        setFields({
          business_hours:      (s.business_hours      || '').slice(0, LIMITS.business_hours),
          human_escalation:    (s.human_escalation    || '').slice(0, LIMITS.human_escalation),
          topics_to_avoid:     (s.topics_to_avoid     || '').slice(0, LIMITS.topics_to_avoid),
          custom_instructions: (s.custom_instructions || '').slice(0, LIMITS.custom_instructions),
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function save() {
    setSaving(true)
    setSaved(false)
    try {
      await fetch(`${API}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  function set(key: FieldKey) {
    return (v: string) => setFields(f => ({ ...f, [key]: v }))
  }

  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex-shrink-0 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Instructions</h1>
            <p className="text-xs text-ink-500 mt-0.5">
              Guide how your agent handles specific situations
            </p>
          </div>
          <div className="flex items-center gap-3">
            <PromptHealth fields={fields} />
            <button
              onClick={save}
              disabled={saving || loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-500 text-white text-sm font-medium hover:bg-accent-600 disabled:opacity-50 transition-colors"
            >
              {saving ? (
                <Loader2 size={14} className="animate-spin" />
              ) : saved ? (
                <CheckCircle size={14} />
              ) : null}
              {saved ? 'Saved' : 'Save changes'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-ink-400">
              <Loader2 size={20} className="animate-spin mr-2" /> Loading…
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-4">

              <Field
                fieldKey="business_hours"
                icon={<Clock size={16} className="text-accent-500" />}
                label="Business hours"
                hint="Agent uses this when callers ask about opening times."
                placeholder="e.g. Monday to Friday, 9am to 6pm IST. Closed on weekends."
                value={fields.business_hours}
                onChange={set('business_hours')}
              />

              <Field
                fieldKey="human_escalation"
                icon={<UserX size={16} className="text-purple-500" />}
                label="When caller asks for a human"
                hint="What should the agent say when someone asks to speak to a person?"
                placeholder="e.g. Apologise and let them know a team member will call back within 2 hours. Take their name and best time to call."
                value={fields.human_escalation}
                onChange={set('human_escalation')}
                multiline
              />

              <Field
                fieldKey="topics_to_avoid"
                icon={<ShieldOff size={16} className="text-red-400" />}
                label="Topics to avoid"
                hint="Subjects the agent should not discuss or comment on."
                placeholder="e.g. Competitor products, ongoing legal matters, internal pricing."
                value={fields.topics_to_avoid}
                onChange={set('topics_to_avoid')}
              />

              <Field
                fieldKey="custom_instructions"
                icon={<StickyNote size={16} className="text-teal-500" />}
                label="Additional instructions"
                hint="Anything specific to your business that doesn't fit above."
                placeholder="e.g. If the caller mentions the word 'urgent', always offer a callback within 30 minutes."
                value={fields.custom_instructions}
                onChange={set('custom_instructions')}
                multiline
              />

              <p className="text-xs text-ink-400 text-center pt-2">
                Keep instructions concise — the shorter they are, the better the agent responds.
              </p>

            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
