'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { CheckCircle, Phone, Loader2 } from 'lucide-react'
import { WebCallModal } from '@/components/calls/WebCallModal'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Voice {
  voice_id: string
  name: string
  description: string
}

interface Language {
  code: string
  name: string
}

interface AgentSettingsFormProps {
  voices: Voice[]
  languages: Language[]
  currentVoiceId: string
  currentAgentName: string
  currentOrgName: string
  currentOrgDescription: string
  currentDefaultLanguage: string
}

export function AgentSettingsForm({
  voices,
  languages,
  currentVoiceId,
  currentAgentName,
  currentOrgName,
  currentOrgDescription,
  currentDefaultLanguage,
}: AgentSettingsFormProps) {
  const [voiceId, setVoiceId] = useState(currentVoiceId)
  const [agentName, setAgentName] = useState(currentAgentName)
  const [orgName, setOrgName] = useState(currentOrgName)
  const [orgDescription, setOrgDescription] = useState(currentOrgDescription)
  const [defaultLanguage, setDefaultLanguage] = useState(currentDefaultLanguage)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [callOpen, setCallOpen] = useState(false)

  const validate = (): string | null => {
    if (!orgName.trim()) return 'Organisation name is required.'
    return null
  }

  const saveSettings = async () => {
    const res = await fetch(`${API}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_voice_id: voiceId,
        agent_name: agentName.trim() || 'aira',
        org_name: orgName.trim(),
        org_description: orgDescription.trim(),
        default_language: defaultLanguage,
      }),
    })
    if (!res.ok) throw new Error('Failed to save')
  }

  const handleSave = async () => {
    const validationError = validate()
    if (validationError) { setError(validationError); return }
    setSaving(true)
    setError(null)
    try {
      await saveSettings()
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Failed to save settings. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleStartCall = async () => {
    const validationError = validate()
    if (validationError) { setError(validationError); return }
    setStarting(true)
    setError(null)
    try {
      await saveSettings()
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      setCallOpen(true)
    } catch {
      setError('Could not save settings before starting call.')
    } finally {
      setStarting(false)
    }
  }

  return (
    <>
      <div className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {saved && (
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700 flex items-center gap-2">
            <CheckCircle size={15} /> Settings saved
          </div>
        )}

        {/* Identity */}
        <div className="bg-white rounded-xl border border-brand-300 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-ink-900">Identity</h2>

          <div>
            <label className="block text-xs font-medium text-ink-700 mb-1.5">Agent name</label>
            <input
              type="text"
              value={agentName}
              onChange={e => setAgentName(e.target.value)}
              placeholder="e.g. aira"
              className="w-full px-3 py-2 rounded-lg border border-brand-300 text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
            />
            <p className="text-xs text-ink-400 mt-1">The name your receptionist uses when greeting callers</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-700 mb-1.5">
              Organisation name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              placeholder="e.g. RandomWalk"
              className={`w-full px-3 py-2 rounded-lg border text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent ${
                !orgName.trim() ? 'border-red-300' : 'border-brand-300'
              }`}
            />
            <p className="text-xs text-ink-400 mt-1">The agent will refer to itself as working at this organisation</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-700 mb-1.5">Organisation description</label>
            <textarea
              value={orgDescription}
              onChange={e => setOrgDescription(e.target.value)}
              placeholder="e.g. RandomWalk is an AI consulting firm that helps businesses build and deploy machine learning solutions. We have offices in Bangalore and Dubai."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-brand-300 text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent resize-none"
            />
            <p className="text-xs text-ink-400 mt-1">Helps the agent understand what the organisation does so it can answer questions naturally</p>
          </div>
        </div>

        {/* Language */}
        <div className="bg-white rounded-xl border border-brand-300 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-ink-900">Default language</h2>
          <p className="text-xs text-ink-400 -mt-2">The agent speaks in this language from the very first word — no switching needed</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {languages.map(lang => {
              const selected = defaultLanguage === lang.code
              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setDefaultLanguage(lang.code)}
                  className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                    selected
                      ? 'border-accent-500 bg-accent-50 text-accent-700 shadow-sm'
                      : 'border-brand-300 text-ink-600 hover:border-accent-300 hover:bg-brand-50'
                  }`}
                >
                  {lang.name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Voice */}
        <div className="bg-white rounded-xl border border-brand-300 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-ink-900">Voice</h2>
          <p className="text-xs text-ink-400 -mt-2">Select the voice your receptionist speaks with</p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {voices.map(voice => {
              const selected = voiceId === voice.voice_id
              return (
                <button
                  key={voice.voice_id}
                  type="button"
                  onClick={() => setVoiceId(voice.voice_id)}
                  className={`relative text-left px-3 py-3 rounded-xl border transition-all ${
                    selected
                      ? 'border-accent-500 bg-accent-50 shadow-sm'
                      : 'border-brand-300 hover:border-accent-300 hover:bg-brand-50'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      selected ? 'bg-accent-500 text-white' : 'bg-brand-200 text-ink-600'
                    }`}>
                      {voice.name[0]}
                    </div>
                    <span className={`text-sm font-semibold ${selected ? 'text-accent-700' : 'text-ink-900'}`}>
                      {voice.name}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-500 leading-tight">{voice.description}</p>
                  {selected && (
                    <div className="absolute top-2 right-2 w-3 h-3 rounded-full bg-accent-500" />
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Save + Test call */}
        <div className="bg-white rounded-xl border border-brand-300 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-ink-900">Save & test</h2>
              <p className="text-xs text-ink-400 mt-0.5">
                Save your settings first, then start a test call to hear how the agent greets callers
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="accent" onClick={handleSave} disabled={saving || starting}>
              {saving ? <><Loader2 size={13} className="animate-spin" /> Saving…</> : 'Save settings'}
            </Button>

            <button
              onClick={handleStartCall}
              disabled={starting || saving}
              className="flex items-center gap-2 px-4 py-2 border border-brand-300 text-ink-700 rounded-xl text-sm font-medium hover:bg-brand-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {starting
                ? <><Loader2 size={14} className="animate-spin" /> Saving…</>
                : <><Phone size={14} /> Start test call</>
              }
            </button>
          </div>
          <p className="text-xs text-ink-400">
            Clicking "Start test call" saves your current settings automatically before connecting.
          </p>
        </div>
      </div>

      {callOpen && <WebCallModal onClose={() => setCallOpen(false)} />}
    </>
  )
}

export default AgentSettingsForm
