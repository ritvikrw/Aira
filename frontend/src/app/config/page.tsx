import AppShell from '@/components/layout/AppShell'
import PromptEditor from '@/components/config/PromptEditor'

export default function ConfigPage() {
  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        <div className="px-6 py-4 border-b border-brand-300 bg-white shrink-0">
          <h1 className="text-lg font-semibold text-ink-900">System Prompt</h1>
          <p className="text-xs text-ink-400 mt-0.5">Define how your AI receptionist behaves on calls</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          <PromptEditor />
        </div>
      </div>
    </AppShell>
  )
}
