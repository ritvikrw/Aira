# AIRA Android app

Native Kotlin/Jetpack Compose client for the AIRA backend (`backend/api`). Talks to the
same FastAPI backend the Next.js dashboard (`frontend/`) uses — both can run side by side.

## Status (Phase 0 + 1 of the mobile rollout)

Built:
- App shell with bottom navigation (Call logs, Analytics, Knowledge base, Config)
- **Call logs**: list of past/active calls, tap through to a call detail screen with
  summary, topics, action items, and full transcript
- **Test call**: live voice call with the AI receptionist over LiveKit — connect, mute,
  end call. Mirrors `frontend/src/components/calls/WebCallModal.tsx`.

Not yet built (still placeholders — see `ui/components/ComingSoonScreen.kt`):
- Analytics dashboard
- Knowledge base manager (upload/crawl/text entry)
- Config (agent settings / voice settings / instructions editor)
- Scheduled calls, Internal metrics (not in the web app's main sidebar either)

## Setup

1. Open the `android/` directory in Android Studio (Ladybug/Koala or newer). Studio will
   offer to generate the Gradle wrapper on first sync — accept it (this repo ships
   `gradle/wrapper/gradle-wrapper.properties` targeting Gradle 8.9, but not the wrapper
   jar itself, so `./gradlew` won't work from a bare checkout until Studio or `gradle
   wrapper` materializes it).
2. Point the backend at something the app can reach:
   - **Emulator**: no setup needed — defaults to `http://10.0.2.2:8000/`, which maps to
     `localhost:8000` on your dev machine.
   - **Physical device on the same wifi**: change the base URL at build time —
     `./gradlew -PbackendBaseUrl=http://<your-lan-ip>:8000/ assembleDebug` — or add a
     settings screen later that calls `BackendSettings.setBaseUrl()`
     (`data/prefs/BackendSettings.kt`) at runtime.
3. Run the backend (`docker-compose up` in `backend/`) — see the prerequisite change below.
4. Run the app.

## Backend prerequisite

The Android app needs `POST /calls/token` on the Python backend to mint LiveKit tokens
(added in `backend/api/routes/livekit_token.py` alongside this app). Make sure:
- `backend/api/requirements.txt` has been reinstalled (`livekit-api` was added)
- `backend/.env` has `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` set
- If testing from a physical device, set `LIVEKIT_PUBLIC_URL` (see `backend/.env.example`)
  to your machine's LAN IP so the phone can actually reach the LiveKit server — `ws://
  localhost:7880` (the default) only works for the emulator or the web app running on
  the same machine.

## Architecture

- MVVM: `ui/<feature>/*ViewModel.kt` expose `StateFlow<UiState>`, screens collect via
  `collectAsStateWithLifecycle()`.
- DI: Hilt (`di/NetworkModule.kt`).
- Networking: Retrofit + kotlinx.serialization, hitting the base URL held in
  `BackendSettings` (DataStore-backed, changeable without rebuilding the app).
- Voice call: `io.livekit:livekit-android` directly (not the compose-components add-on)
  — `ui/call/LiveCallViewModel.kt` connects, tracks `Room.State` and
  `remoteParticipants` as flows, and controls the mic via `localParticipant
  .setMicrophoneEnabled()`. The client never calls `/calls/{id}/end` — like the web app,
  the call record lifecycle is owned by `backend/voice_agent`, not the client.

## Known gap

This was scaffolded without a local JDK/Android SDK/Gradle available, so none of it has
been compiled or run yet — review it in Android Studio and fix anything that doesn't
build before relying on it.
