'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, CheckCircle2 } from 'lucide-react'

function Field({ label, name, placeholder, hint, secret, required }: {
  label: string; name: string; placeholder?: string; hint?: string; secret?: boolean; required?: boolean
}) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label className="block text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-1.5">
        {label}{required && <span className="text-[#C4621A] ml-1">*</span>}
      </label>
      <div className="relative">
        <input
          name={name}
          type={secret && !show ? 'password' : 'text'}
          placeholder={placeholder}
          required={required}
          className="w-full bg-[#162335] border border-[#1F3450] rounded-lg px-3 py-2.5 text-sm text-[#EDF2F7] placeholder-[#2A4A6E] focus:outline-none focus:border-[#C4621A] transition-colors font-mono pr-9"
        />
        {secret && (
          <button type="button" onClick={() => setShow(s => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5E7A95] hover:text-[#C4D4E3]">
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
      {hint && <p className="text-[11px] text-[#5E7A95] mt-1">{hint}</p>}
    </div>
  )
}

export function NewClientForm() {
  const router = useRouter()
  const [done, setDone] = useState(false)

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setDone(true)
  }

  if (done) {
    return (
      <div className="bg-[#111E2E] border border-[#00C9A7]/30 rounded-xl p-8 text-center">
        <CheckCircle2 size={40} className="text-[#00C9A7] mx-auto mb-4" />
        <h2 className="text-lg font-bold text-[#EDF2F7] mb-2">Client created</h2>
        <p className="text-sm text-[#5E7A95] mb-6">
          A password setup email has been sent to the client. They can log in once they set their password.
        </p>
        <a href="/clients"
          className="bg-[#C4621A] hover:bg-[#E06B28] text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors">
          Back to clients
        </a>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6 space-y-4">
        <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95]">Identity</h2>
        <Field label="Company name" name="name" placeholder="Acme Corp" required />
        <Field label="Slug" name="slug" placeholder="acme"
          hint="Lowercase letters and hyphens only. Used in room names — cannot be changed later." required />
      </div>

      <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6 space-y-4">
        <div>
          <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95]">Dashboard login</h2>
          <p className="text-[11px] text-[#5E7A95] mt-1">Client uses these to log into their dashboard.</p>
        </div>
        <Field label="Email" name="email" placeholder="admin@acmecorp.com" required />
        <Field label="Temporary password" name="password" placeholder="They will be prompted to change on first login" secret required />
      </div>

      <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-6 space-y-4">
        <div>
          <h2 className="text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95]">Client API keys</h2>
          <p className="text-[11px] text-[#5E7A95] mt-1">All optional — only add what the client has provided.</p>
        </div>
        <Field label="Sarvam API key" name="sarvam_key" placeholder="sk-sarvam-…" secret />
        <Field label="Cartesia API key" name="cartesia_key" placeholder="sk-cartesia-…" secret />
        <Field label="OpenAI API key" name="openai_key" placeholder="sk-openai-…" secret />
        <Field label="Google / Gemini API key" name="google_key" placeholder="AIza…" secret />
        <Field label="ElevenLabs API key" name="elevenlabs_key" placeholder="el-…" secret />
      </div>

      <div className="flex gap-3">
        <button type="submit"
          className="bg-[#C4621A] hover:bg-[#E06B28] text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition-colors">
          Create client
        </button>
        <a href="/clients" className="text-sm text-[#5E7A95] hover:text-[#C4D4E3] px-4 py-2.5 transition-colors">
          Cancel
        </a>
      </div>
    </form>
  )
}
