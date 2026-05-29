'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  PhoneIncoming,
  Clock,
  BarChart2,
  BookOpen,
  Settings2,
  FlaskConical,
  StickyNote,
  LucideIcon,
} from 'lucide-react'

interface NavItemProps {
  href: string
  icon: LucideIcon
  label: string
  badge?: number
}

function NavItem({ href, icon: Icon, label, badge }: NavItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || pathname.startsWith(href + '/')

  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm mb-0.5 transition-colors ${
        isActive
          ? 'bg-white border-l-2 border-accent-500 text-ink-900 font-medium shadow-sm'
          : 'text-ink-600 hover:bg-brand-100'
      }`}
    >
      <Icon size={16} className={isActive ? 'text-accent-500' : 'text-ink-400'} />
      <span className="flex-1">{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-accent-500 text-white text-[10px] font-semibold">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </Link>
  )
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export function Sidebar() {
  const [activeBadge, setActiveBadge] = useState(0)
  const [agentName, setAgentName] = useState('aira')

  useEffect(() => {
    async function load() {
      try {
        const [overviewRes, settingsRes] = await Promise.all([
          fetch(`${API}/calls/analytics/overview`),
          fetch(`${API}/settings`),
        ])
        if (overviewRes.ok) {
          const data = await overviewRes.json() as { active_calls?: number }
          setActiveBadge(data.active_calls || 0)
        }
        if (settingsRes.ok) {
          const s = await settingsRes.json() as { agent_name?: string }
          if (s.agent_name) setAgentName(s.agent_name)
        }
      } catch { /* ignore */ }
    }
    load()
    const interval = setInterval(load, 30_000)
    return () => clearInterval(interval)
  }, [])

  return (
    <aside className="w-[220px] min-h-screen bg-brand-200 border-r border-brand-300 flex flex-col flex-shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-brand-300">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-accent-500 rotate-45 rounded-sm flex-shrink-0" />
          <span className="text-xl font-semibold font-serif text-ink-900 tracking-tight">
            aira
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4">
        <p className="text-[10px] font-semibold tracking-widest text-ink-400 uppercase px-2 mb-2">
          Main
        </p>
        <NavItem href="/analytics" icon={BarChart2} label="Analytics" />
        <NavItem href="/dashboard" icon={PhoneIncoming} label="Call logs" badge={activeBadge} />
        <NavItem href="/scheduled" icon={Clock} label="Scheduled" />

        <p className="text-[10px] font-semibold tracking-widest text-ink-400 uppercase px-2 mt-5 mb-2">
          Config
        </p>
        <NavItem href="/config/knowledge-base" icon={BookOpen} label="Knowledge base" />
        <NavItem href="/config/agent-settings" icon={Settings2} label="Agent settings" />
        <NavItem href="/config/instructions" icon={StickyNote} label="Instructions" />

        <p className="text-[10px] font-semibold tracking-widest text-ink-400 uppercase px-2 mt-5 mb-2">
          System
        </p>
        <NavItem href="/internal" icon={FlaskConical} label="Internal" />
      </nav>

      {/* Status footer */}
      <div className="px-4 py-4 border-t border-brand-300">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink-900 truncate">{agentName}</p>
            <p className="text-xs text-ink-500 truncate">Live · Agent online</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
