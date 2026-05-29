'use client'

import { useState } from 'react'
import { PhoneCall, X, Info } from 'lucide-react'
import Button from '@/components/ui/Button'

export default function TestCallButton() {
  const [showInfo, setShowInfo] = useState(false)

  return (
    <div className="relative">
      <Button variant="accent" size="md" onClick={() => setShowInfo(s => !s)}>
        <PhoneCall className="w-4 h-4" />
        Test Call
      </Button>

      {showInfo && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setShowInfo(false)} />
          <div className="absolute right-0 top-11 z-50 w-72 bg-white border border-brand-300 rounded-xl shadow-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-accent-500" />
                <p className="text-sm font-semibold text-ink-900">Test Call</p>
              </div>
              <button onClick={() => setShowInfo(false)} className="text-ink-400 hover:text-ink-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-ink-600 leading-relaxed mb-3">
              To test via voice, run the agent in console mode from your terminal:
            </p>
            <code className="block bg-ink-900 text-green-400 text-xs rounded-lg p-3 font-mono leading-relaxed">
              cd RECEP/backend/voice_agent<br />
              python main.py console
            </code>
            <p className="text-xs text-ink-400 mt-3">
              Twilio integration coming soon — calls will appear here automatically once configured.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
