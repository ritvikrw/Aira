import React from 'react'

type BadgeStatus = 'pending' | 'resolved' | 'urgent' | 'scheduled' | 'active' | 'ended' | string

interface BadgeProps {
  status: BadgeStatus
  className?: string
}

const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  pending:   { bg: 'bg-[#FDF4EC]', text: 'text-[#C4621A]', label: 'Pending' },
  active:    { bg: 'bg-[#FDF4EC]', text: 'text-[#C4621A]', label: 'Active' },
  resolved:  { bg: 'bg-[#ECFDF5]', text: 'text-[#166534]', label: 'Resolved' },
  ended:     { bg: 'bg-[#ECFDF5]', text: 'text-[#166534]', label: 'Ended' },
  urgent:    { bg: 'bg-[#FEF2F2]', text: 'text-[#991B1B]', label: 'Urgent' },
  scheduled: { bg: 'bg-blue-50',   text: 'text-blue-700',  label: 'Scheduled' },
  processing:{ bg: 'bg-accent-50', text: 'text-accent-600',label: 'Processing' },
  ready:     { bg: 'bg-[#ECFDF5]', text: 'text-[#166534]', label: 'Ready' },
  error:     { bg: 'bg-[#FEF2F2]', text: 'text-[#991B1B]', label: 'Error' },
}

export function Badge({ status, className = '' }: BadgeProps) {
  const config = statusConfig[status] || {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    label: status,
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text} ${className}`}
    >
      {config.label}
    </span>
  )
}

export default Badge
