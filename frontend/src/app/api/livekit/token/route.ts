import { NextResponse } from 'next/server'
import { AccessToken, RoomServiceClient } from 'livekit-server-sdk'

const LIVEKIT_URL = process.env.LIVEKIT_URL
const API_KEY = process.env.LIVEKIT_API_KEY
const API_SECRET = process.env.LIVEKIT_API_SECRET

export const revalidate = 0

export async function POST() {
  if (!LIVEKIT_URL || !API_KEY || !API_SECRET) {
    return NextResponse.json({ error: 'LiveKit not configured' }, { status: 503 })
  }

  const roomName = `web-${crypto.randomUUID().split('-')[0]}-${Date.now()}`
  const participantIdentity = `web-caller-${crypto.randomUUID().split('-')[0]}`

  // Pre-create the room so the agent worker can be dispatched immediately
  const roomService = new RoomServiceClient(LIVEKIT_URL, API_KEY, API_SECRET)
  try {
    await roomService.createRoom({ name: roomName, emptyTimeout: 300, maxParticipants: 10 })
    console.log('Room created:', roomName)
  } catch {
    // Room may already exist — not fatal
  }

  // Generate participant token with RoomConfiguration for agent auto-dispatch
  const at = new AccessToken(API_KEY, API_SECRET, {
    identity: participantIdentity,
    name: 'Web Caller',
    ttl: '15m',
  })
  at.addGrant({ room: roomName, roomJoin: true, canPublish: true, canSubscribe: true, canPublishData: true })

  const participantToken = await at.toJwt()
  console.log('Token generated for room:', roomName)

  const wsUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL || LIVEKIT_URL
  return NextResponse.json(
    { serverUrl: wsUrl, participantToken, roomName },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
