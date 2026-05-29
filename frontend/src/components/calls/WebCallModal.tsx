'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Phone, PhoneOff, Mic, MicOff, X, Radio, Loader2, Volume2, CheckCircle } from 'lucide-react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  useConnectionState,
  useLocalParticipant,
  useRoomContext,
  useRemoteParticipants,
} from '@livekit/components-react'
import { ConnectionState } from 'livekit-client'

interface WebCallModalProps {
  onClose: () => void
}

// Inner component — rendered inside LiveKitRoom context
function CallInner({ onEnd }: { onEnd: () => void }) {
  const connectionState = useConnectionState()
  const { localParticipant } = useLocalParticipant()
  const room = useRoomContext()
  const remoteParticipants = useRemoteParticipants()
  const [muted, setMuted] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [connectionState])

  const agentConnected = remoteParticipants.length > 0

  const toggleMute = useCallback(async () => {
    if (!localParticipant) return
    const enabled = localParticipant.isMicrophoneEnabled
    await localParticipant.setMicrophoneEnabled(!enabled)
    setMuted(enabled)
  }, [localParticipant])

  const handleEnd = useCallback(async () => {
    await room.disconnect()
    onEnd()
  }, [room, onEnd])

  const fmt = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  if (connectionState === ConnectionState.Connecting) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <Loader2 size={32} className="text-accent-500 animate-spin mb-3" />
        <p className="text-sm text-ink-600">Connecting…</p>
      </div>
    )
  }

  if (connectionState === ConnectionState.Connected) {
    return (
      <>
        <StartAudio label="Tap to enable audio" />

        <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
          <div className="relative">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center ${agentConnected ? 'bg-red-100' : 'bg-brand-100'}`}>
              <Radio size={28} className={agentConnected ? 'text-red-500' : 'text-ink-400'} />
            </div>
            {agentConnected && (
              <span className="absolute inset-0 rounded-full border-2 border-red-400 animate-ping opacity-40" />
            )}
          </div>
          <div>
            <p className="text-sm font-medium text-ink-700">
              {agentConnected ? 'aira is listening…' : 'Waiting for aira to join…'}
            </p>
            <p className="text-xs text-ink-400 mt-0.5">
              {agentConnected ? `${fmt(elapsed)} · Speak naturally` : 'The agent is being dispatched'}
            </p>
          </div>
        </div>

        <div className="px-5 py-4 border-t border-brand-100 flex items-center justify-between">
          <button
            onClick={toggleMute}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              muted ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-brand-100 text-ink-700 hover:bg-brand-200'
            }`}
          >
            {muted ? <MicOff size={15} /> : <Mic size={15} />}
            {muted ? 'Unmute' : 'Mute'}
          </button>
          <button
            onClick={handleEnd}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-xl text-sm font-medium hover:bg-red-600 transition-colors"
          >
            <PhoneOff size={15} /> End call
          </button>
        </div>
      </>
    )
  }

  return null
}

export function WebCallModal({ onClose }: WebCallModalProps) {
  const [phase, setPhase] = useState<'idle' | 'live' | 'ended'>('idle')
  const [token, setToken] = useState('')
  const [serverUrl, setServerUrl] = useState('')
  const [error, setError] = useState('')

  const startCall = async () => {
    setError('')
    try {
      const res = await fetch('/api/livekit/token', { method: 'POST' })
      if (!res.ok) { setError('Could not start call. Is LiveKit running?'); return }
      const data = await res.json() as { serverUrl: string; participantToken: string; roomName: string }
      setServerUrl(data.serverUrl)
      setToken(data.participantToken)
      setPhase('live')
    } catch {
      setError('Connection failed. Check that LiveKit server is running.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden flex flex-col" style={{ maxHeight: '90vh' }}>

        {/* Header */}
        <div className={`px-5 py-4 flex items-center justify-between flex-shrink-0 ${
          phase === 'live'  ? 'bg-red-50 border-b border-red-100' :
          phase === 'ended' ? 'bg-brand-50 border-b border-brand-200' :
                              'bg-white border-b border-brand-200'
        }`}>
          <div className="flex items-center gap-3">
            {phase === 'live' && <Radio size={15} className="text-red-500 animate-pulse" />}
            <div>
              <p className="text-sm font-semibold text-ink-900">
                {phase === 'idle'  && 'Test call'}
                {phase === 'live'  && 'Live call'}
                {phase === 'ended' && 'Call ended'}
              </p>
              <p className="text-xs text-ink-500">Talking to aira</p>
            </div>
          </div>
          {phase !== 'live' && (
            <button onClick={onClose} className="text-ink-400 hover:text-ink-700 transition-colors">
              <X size={18} />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto min-h-0">

          {/* IDLE */}
          {phase === 'idle' && (
            <div className="flex flex-col items-center justify-center py-8 text-center p-5">
              <div className="w-16 h-16 rounded-full bg-accent-100 flex items-center justify-center mb-4">
                <Phone size={24} className="text-accent-600" />
              </div>
              <p className="text-sm text-ink-600 mb-1">Start a live call with your AI receptionist</p>
              <p className="text-xs text-ink-400 mb-6">
                Make sure the voice agent is running and your microphone is allowed
              </p>
              {error && (
                <p className="text-xs text-red-500 mb-4 bg-red-50 px-3 py-2 rounded-lg w-full text-left">{error}</p>
              )}
              <button
                onClick={startCall}
                className="flex items-center gap-2 px-6 py-3 bg-accent-500 text-white rounded-xl font-medium text-sm hover:bg-accent-600 transition-colors"
              >
                <Phone size={16} /> Start call
              </button>
            </div>
          )}

          {/* LIVE */}
          {phase === 'live' && token && serverUrl && (
            <LiveKitRoom
              token={token}
              serverUrl={serverUrl}
              connect={true}
              audio={true}
              video={false}
              onDisconnected={() => setPhase('ended')}
              onError={(err) => {
                console.error('LiveKit error:', err)
                setToken('')
                setServerUrl('')
                setError(`Connection error: ${err.message}`)
                setPhase('idle')
              }}
              className="flex flex-col"
            >
              <RoomAudioRenderer />
              <CallInner onEnd={() => setPhase('ended')} />
            </LiveKitRoom>
          )}

          {/* ENDED */}
          {phase === 'ended' && (
            <div className="flex flex-col items-center justify-center py-12 text-center px-5 gap-3">
              <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle size={24} className="text-green-600" />
              </div>
              <p className="text-sm font-medium text-ink-900">Call completed</p>
              <p className="text-xs text-ink-400">
                The transcript and summary are available in Today's calls
              </p>
            </div>
          )}
        </div>

        {/* Footer for ended state */}
        {phase === 'ended' && (
          <div className="px-5 py-4 border-t border-brand-100 flex-shrink-0">
            <button
              onClick={onClose}
              className="w-full py-2.5 bg-ink-900 text-white rounded-xl text-sm font-medium hover:bg-ink-800 transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default WebCallModal
