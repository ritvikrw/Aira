'use client'

import { AdminShell } from '@/components/layout/AdminShell'
import { NewClientForm } from '@/components/clients/NewClientForm'

export default function NewClientPage() {
  return (
    <AdminShell>
      <div className="p-8 max-w-2xl">
        <div className="mb-8">
          <a href="/clients" className="text-xs text-[#5E7A95] hover:text-[#C4D4E3] transition-colors">← Back to clients</a>
          <h1 className="text-xl font-bold text-[#EDF2F7] mt-3">Add new client</h1>
          <p className="text-sm text-[#5E7A95] mt-1">
            Each client brings their own API keys — you provide the platform.
          </p>
        </div>
        <NewClientForm />
      </div>
    </AdminShell>
  )
}
