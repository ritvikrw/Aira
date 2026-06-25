'use client'

import { useEffect, useState } from 'react'
import { Check, Loader2, Volume2 } from 'lucide-react'
import Button from '@/components/ui/Button'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Voice { voice_id: string; name: string; description: string }

export default function VoiceSettings() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [selected, setSelected] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API}/settings/voices`).then(r => r.json()),
      fetch(`${API}/settings`).then(r => r.json()),
    ]).then(([v, s]) => {
      setVoices(v)
      setSelected(s.selected_voice_id || v[0]?.voice_id)
    }).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    await fetch(`${API}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_voice_id: selected }),
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24 text-ink-400">
      <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading voices…
    </div>
  )

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="grid grid-cols-1 gap-3">
        {voices.map(voice => {
          const isSelected = selected === voice.voice_id
          return (
            <button
              key={voice.voice_id}
              onClick={() => setSelected(voice.voice_id)}
              className={`w-full text-left rounded-xl border-2 p-4 transition-all ${
                isSelected
                  ? 'border-accent-500 bg-accent-50'
                  : 'border-brand-300 bg-white hover:border-accent-300 hover:bg-brand-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isSelected ? 'bg-accent-500' : 'bg-brand-200'
                  }`}>
                    <Volume2 className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-ink-500'}`} />
                  </div>
                  <div>
                    <p className={`text-sm font-semibold ${isSelected ? 'text-accent-700' : 'text-ink-900'}`}>
                      {voice.name}
                    </p>
                    <p className="text-xs text-ink-400 mt-0.5">{voice.description}</p>
                  </div>
                </div>
                {isSelected && (
                  <div className="w-6 h-6 rounded-full bg-accent-500 flex items-center justify-center">
                    <Check className="w-3.5 h-3.5 text-white" />
                  </div>
                )}
              </div>
            </button>
          )
        })}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-brand-200">
        <p className="text-xs text-ink-400">
          Voice change takes effect on the next call
        </p>
        <Button variant="accent" onClick={handleSave} disabled={saving}>
          {saving ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving…</> : saved ? <><Check className="w-3.5 h-3.5" /> Saved!</> : 'Save voice'}
        </Button>
      </div>
    </div>
  )
}
