'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Users, BarChart2, LogOut, Plus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

function NavItem({ href, icon: Icon, label }: { href: string; icon: LucideIcon; label: string }) {
  const pathname = usePathname()
  const active = pathname === href || pathname.startsWith(href + '/')
  return (
    <Link href={href}
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm mb-0.5 transition-colors ${
        active
          ? 'bg-[#162335] border-l-2 border-[#C4621A] text-[#EDF2F7] font-medium'
          : 'text-[#5E7A95] hover:bg-[#111E2E] hover:text-[#C4D4E3]'
      }`}>
      <Icon size={15} className={active ? 'text-[#C4621A]' : 'text-[#5E7A95]'} />
      {label}
    </Link>
  )
}

export function Sidebar() {
  const router = useRouter()

  function signOut() {
    localStorage.removeItem('admin_auth')
    router.push('/login')
  }

  return (
    <aside className="w-[220px] min-h-screen bg-[#0D1A28] border-r border-[#1F3450] flex flex-col flex-shrink-0">
      <div className="px-5 py-5 border-b border-[#1F3450]">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 bg-[#C4621A] rotate-45 rounded-sm flex-shrink-0" />
          <span className="text-lg font-bold text-[#EDF2F7] tracking-tight">RECEP</span>
          <span className="text-[9px] font-bold tracking-widest uppercase text-[#5E7A95] mt-0.5">Admin</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4">
        <p className="text-[9px] font-semibold tracking-widest text-[#2A4A6E] uppercase px-2 mb-2">Platform</p>
        <NavItem href="/clients" icon={Users} label="Clients" />
        <NavItem href="/analytics" icon={BarChart2} label="Analytics" />

        <div className="mt-4 px-2">
          <Link href="/clients/new"
            className="flex items-center gap-2 text-xs font-semibold text-[#C4621A] hover:text-[#E06B28] transition-colors">
            <Plus size={13} /> Add client
          </Link>
        </div>
      </nav>

      <div className="px-3 py-4 border-t border-[#1F3450]">
        <button onClick={signOut}
          className="flex items-center gap-2 text-xs text-[#5E7A95] hover:text-[#FF5F6D] transition-colors w-full px-2 py-1.5 rounded">
          <LogOut size={13} /> Sign out
        </button>
      </div>
    </aside>
  )
}
