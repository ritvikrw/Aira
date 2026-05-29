export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (secs === 0) return `${mins}m`
  return `${mins}m ${secs}s`
}

export function formatPhone(phone: string): string {
  if (!phone) return 'Unknown'
  if (phone.startsWith('+91') && phone.length === 13) {
    const num = phone.slice(3)
    return `+91 ${num.slice(0, 5)} ${num.slice(5)}`
  }
  return phone
}
