'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Shield } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const fd = new FormData(e.currentTarget)
    const pw = fd.get('password') as string
    setTimeout(() => {
      if (pw === 'admin') {
        localStorage.setItem('admin_auth', '1')
        router.push('/clients')
      } else {
        setError('Invalid password. (Hint: admin)')
        setLoading(false)
      }
    }, 400)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0B1622]">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-10 justify-center">
          <div className="w-7 h-7 bg-[#C4621A] rotate-45 rounded-sm" />
          <span className="text-2xl font-bold text-[#EDF2F7] tracking-tight">RECEP</span>
          <span className="text-[10px] font-bold tracking-widest uppercase text-[#5E7A95] mt-1">Admin</span>
        </div>

        <div className="bg-[#111E2E] border border-[#1F3450] rounded-xl p-8">
          <div className="flex items-center gap-2 mb-6">
            <Shield size={15} className="text-[#C4621A]" />
            <h1 className="text-[#EDF2F7] font-semibold">Admin access</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[10px] font-semibold tracking-widest uppercase text-[#5E7A95] mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  name="password"
                  type={show ? 'text' : 'password'}
                  required
                  autoFocus
                  className="w-full bg-[#162335] border border-[#1F3450] rounded-lg px-4 py-2.5 text-sm text-[#EDF2F7] placeholder-[#2A4A6E] focus:outline-none focus:border-[#C4621A] transition-colors pr-10"
                  placeholder="Enter admin password"
                />
                <button type="button" onClick={() => setShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5E7A95] hover:text-[#C4D4E3]">
                  {show ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-xs text-[#FF5F6D] bg-[#FF5F6D]/10 border border-[#FF5F6D]/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button type="submit" disabled={loading}
              className="w-full bg-[#C4621A] hover:bg-[#E06B28] disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-[#2A4A6E] mt-6">RECEP Platform · Admin Console</p>
      </div>
    </div>
  )
}
