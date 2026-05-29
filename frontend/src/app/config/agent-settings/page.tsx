import { AppShell } from '@/components/layout/AppShell'
import { AgentSettingsForm } from '@/components/config/AgentSettingsForm'

export const dynamic = 'force-dynamic'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export default async function AgentSettingsPage() {
  let voices: Array<{ voice_id: string; name: string; description: string }> = []
  let languages: Array<{ code: string; name: string }> = []
  let currentVoiceId = 'sarvam:anushka'
  let currentAgentName = 'aira'
  let currentOrgName = ''
  let currentOrgDescription = ''
  let currentDefaultLanguage = 'en-IN'

  try {
    const [voicesRes, languagesRes, settingsRes] = await Promise.all([
      fetch(`${API}/settings/voices`, { cache: 'no-store' }),
      fetch(`${API}/settings/languages`, { cache: 'no-store' }),
      fetch(`${API}/settings`, { cache: 'no-store' }),
    ])
    if (voicesRes.ok) voices = await voicesRes.json()
    if (languagesRes.ok) languages = await languagesRes.json()
    if (settingsRes.ok) {
      const s = await settingsRes.json() as {
        selected_voice_id?: string
        agent_name?: string
        org_name?: string
        org_description?: string
        default_language?: string
      }
      currentVoiceId = s.selected_voice_id || currentVoiceId
      currentAgentName = s.agent_name || currentAgentName
      currentOrgName = s.org_name || currentOrgName
      currentOrgDescription = s.org_description || currentOrgDescription
      currentDefaultLanguage = s.default_language || currentDefaultLanguage
    }
  } catch { /* ignore */ }

  return (
    <AppShell>
      <div className="flex flex-col h-screen">
        <div className="px-6 py-4 border-b border-brand-300 bg-white flex-shrink-0">
          <h1 className="text-lg font-semibold text-ink-900">Agent settings</h1>
          <p className="text-xs text-ink-500 mt-0.5">
            Configure your AI receptionist's identity, voice, and run a test call
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto">
            <AgentSettingsForm
              voices={voices}
              languages={languages}
              currentVoiceId={currentVoiceId}
              currentAgentName={currentAgentName}
              currentOrgName={currentOrgName}
              currentOrgDescription={currentOrgDescription}
              currentDefaultLanguage={currentDefaultLanguage}
            />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
