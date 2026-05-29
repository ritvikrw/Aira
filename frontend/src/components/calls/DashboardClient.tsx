'use client'

import { useState } from 'react'
import { CallList } from './CallList'
import { CallDetail } from './CallDetail'
import { CallData } from './CallCard'

interface DashboardClientProps {
  calls: CallData[]
  agentName?: string
}

export function DashboardClient({ calls, agentName }: DashboardClientProps) {
  const [selectedId, setSelectedId] = useState<string>('')

  const selectedCall = selectedId ? (calls.find((c) => c.session_id === selectedId) ?? null) : null

  return (
    <>
      <CallList
        calls={calls}
        selectedCallId={selectedId}
        onSelectCall={setSelectedId}
      />
      <CallDetail call={selectedCall} agentName={agentName} />
    </>
  )
}

export default DashboardClient
