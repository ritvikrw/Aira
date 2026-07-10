package com.randomwalk.aira.ui.call

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.randomwalk.aira.data.repository.CallsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import io.livekit.android.LiveKit
import io.livekit.android.room.Room
import io.livekit.android.util.flow
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class CallPhase { IDLE, CONNECTING, LIVE, ENDED, ERROR }

data class LiveCallUiState(
    val phase: CallPhase = CallPhase.IDLE,
    val agentJoined: Boolean = false,
    val muted: Boolean = false,
    val elapsedSeconds: Int = 0,
    val errorMessage: String? = null,
)

@HiltViewModel
class LiveCallViewModel @Inject constructor(
    @ApplicationContext private val appContext: Context,
    private val repository: CallsRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LiveCallUiState())
    val uiState: StateFlow<LiveCallUiState> = _uiState.asStateFlow()

    private var room: Room? = null
    private var timerJob: Job? = null

    fun startCall() {
        if (_uiState.value.phase == CallPhase.CONNECTING || _uiState.value.phase == CallPhase.LIVE) return
        _uiState.value = LiveCallUiState(phase = CallPhase.CONNECTING)

        viewModelScope.launch {
            val tokenResult = runCatching { repository.createCallToken() }
            val tokenResponse = tokenResult.getOrNull()
            if (tokenResponse == null) {
                _uiState.value = LiveCallUiState(
                    phase = CallPhase.ERROR,
                    errorMessage = "Could not start call. Is the backend and LiveKit server running?",
                )
                return@launch
            }

            val newRoom = LiveKit.create(appContext)
            room = newRoom

            newRoom::state.flow
                .onEach { state ->
                    if (state == Room.State.CONNECTED) {
                        _uiState.value = _uiState.value.copy(phase = CallPhase.LIVE)
                        startTimer()
                    }
                }
                .launchIn(viewModelScope)

            newRoom::remoteParticipants.flow
                .onEach { participants ->
                    _uiState.value = _uiState.value.copy(agentJoined = participants.isNotEmpty())
                }
                .launchIn(viewModelScope)

            runCatching {
                newRoom.connect(tokenResponse.serverUrl, tokenResponse.participantToken)
                newRoom.localParticipant.setMicrophoneEnabled(true)
            }.onFailure { e ->
                _uiState.value = LiveCallUiState(
                    phase = CallPhase.ERROR,
                    errorMessage = "Connection error: ${e.message}",
                )
                newRoom.disconnect()
                room = null
            }
        }
    }

    fun toggleMute() {
        val current = room ?: return
        val newMuted = !_uiState.value.muted
        viewModelScope.launch {
            runCatching { current.localParticipant.setMicrophoneEnabled(!newMuted) }
                .onSuccess { _uiState.value = _uiState.value.copy(muted = newMuted) }
        }
    }

    fun endCall() {
        timerJob?.cancel()
        room?.disconnect()
        room = null
        _uiState.value = _uiState.value.copy(phase = CallPhase.ENDED)
    }

    private fun startTimer() {
        timerJob?.cancel()
        timerJob = viewModelScope.launch {
            while (true) {
                delay(1000)
                _uiState.value = _uiState.value.copy(elapsedSeconds = _uiState.value.elapsedSeconds + 1)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        timerJob?.cancel()
        room?.disconnect()
    }
}
