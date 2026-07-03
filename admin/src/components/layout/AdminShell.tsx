'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from './Sidebar'

export function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  useEffect(() => {
    if (!localStorage.getItem('admin_auth')) {
      router.replace('/login')
    }
  }, [router])

  return (
    <div className="flex min-h-screen bg-[#0B1622]">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-auto">{children}</main>
    </div>
  )
}
