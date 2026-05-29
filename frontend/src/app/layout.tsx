import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'aira — AI Receptionist',
  description: 'AI-powered receptionist dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
