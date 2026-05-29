import { redirect } from 'next/navigation'

export default function VoiceSettingsRedirect() {
  redirect('/config/agent-settings')
}
