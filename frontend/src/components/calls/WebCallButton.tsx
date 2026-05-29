'use client'

import { useState } from 'react'
import { Phone } from 'lucide-react'
import { WebCallModal } from './WebCallModal'

export function WebCallButton() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-accent-500 text-white rounded-xl text-sm font-medium hover:bg-accent-600 transition-colors shadow-sm"
      >
        <Phone size={14} />
        Test call
      </button>
      {open && <WebCallModal onClose={() => setOpen(false)} />}
    </>
  )
}

export default WebCallButton
