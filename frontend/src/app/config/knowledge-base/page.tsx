import { AppShell } from '@/components/layout/AppShell'
import { KnowledgeBaseEditor } from '@/components/config/KnowledgeBaseEditor'

export const dynamic = 'force-dynamic'

export default function KnowledgeBasePage() {
  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex-shrink-0">
          <h1 className="text-lg font-semibold text-ink-900">Knowledge base</h1>
          <p className="text-xs text-ink-500 mt-0.5">
            Upload documents or crawl your website for aira to reference during calls
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            <KnowledgeBaseEditor />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
