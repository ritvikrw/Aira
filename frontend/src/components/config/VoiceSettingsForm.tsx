'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { CheckCircle } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Voice {
  voice_id: string
  name: string
  description: string
}

interface VoiceSettingsFormProps {
  voices: Voice[]
  currentVoiceId: string
}

export function VoiceSettingsForm({ voices, currentVoiceId }: VoiceSettingsFormProps) {
  const [voiceId, setVoiceId] = useState(currentVoiceId)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await fetch(`${API}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_voice_id: voiceId }),
      })
      if (!res.ok) throw new Error('Failed to save')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Failed to save settings. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-brand-300 p-6 space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {saved && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle size={15} />
          Voice settings saved
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-ink-700 mb-3">Choose voice</label>
        <p className="text-xs text-ink-400 mb-4">
          Select the voice Aira uses when answering calls
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {voices.map(voice => {
            const selected = voiceId === voice.voice_id
            const initial = voice.name[0]
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
                    {initial}
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

      <div className="pt-2">
        <Button variant="accent" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save voice'}
        </Button>
      </div>
    </div>
  )
}

export default VoiceSettingsForm
