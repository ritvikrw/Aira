'use client'

import { useState } from 'react'
import { Save, Info } from 'lucide-react'
import Button from '@/components/ui/Button'

const DEFAULT_PROMPT = `You are an AI receptionist. Your job is to answer incoming calls, help callers with their questions, and take messages when needed.

## Behaviour
- Greet callers warmly and professionally
- Listen carefully to understand what they need
- Use the search_knowledge_base tool to look up accurate information before answering questions
- If the knowledge base has no relevant information, say so honestly and offer to take a message
- Keep responses concise — this is a phone call, not a chat
- Speak naturally; avoid bullet points or markdown in your responses
- If a caller wants to leave a message, collect: their name, contact number, and the message
- If a caller is upset, stay calm and empathetic

## Limitations
- Do not make up information. Only answer from the knowledge base or general public knowledge
- Do not commit to specific appointments, prices, or policies unless confirmed in the knowledge base
- If a question is beyond your ability, politely say you will pass it to a human colleague

## Ending the call
- Before ending, confirm you have answered everything the caller needed
- Thank them for calling`

export default function PromptEditor() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    // In a full implementation this would POST to the API
    // For now just show confirmation — the actual prompt lives in voice_agent/prompts.py
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="p-6 max-w-3xl space-y-4">
      <div className="bg-accent-50 border border-accent-200 rounded-xl px-4 py-3 flex gap-3 text-sm text-accent-700">
        <Info className="w-4 h-4 mt-0.5 shrink-0" />
        <span>
          The live prompt is defined in <code className="bg-accent-100 px-1 rounded text-xs">voice_agent/prompts.py</code>.
          Edit it there for permanent changes. This editor is a reference view.
        </span>
      </div>

      <div className="bg-white border border-brand-300 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-brand-200 flex items-center justify-between">
          <p className="text-xs font-semibold text-ink-500 uppercase tracking-wide">System prompt</p>
          <Button variant="accent" size="sm" onClick={handleSave}>
            <Save className="w-3 h-3" />
            {saved ? 'Saved!' : 'Save'}
          </Button>
        </div>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          className="w-full h-[500px] p-4 text-sm text-ink-800 font-mono resize-none focus:outline-none"
          spellCheck={false}
        />
      </div>
    </div>
  )
}
