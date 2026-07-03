'use client'

import { use } from 'react'
import { MOCK_CLIENTS, MOCK_CALLS } from '@/lib/mock'
import { AdminShell } from '@/components/layout/AdminShell'
import { ClientDetail } from '@/components/clients/ClientDetail'
import { notFound } from 'next/navigation'

export default function ClientPage({ params }: { params: { id: string } }) {
  const client = MOCK_CLIENTS.find(c => c.id === params.id)
  if (!client) notFound()
  const calls = MOCK_CALLS[client.id] || []
  return (
    <AdminShell>
      <ClientDetail client={client} calls={calls} />
    </AdminShell>
  )
}
