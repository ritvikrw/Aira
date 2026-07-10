package com.randomwalk.aira.ui.dashboard

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.randomwalk.aira.data.network.dto.CallDetail
import com.randomwalk.aira.data.network.dto.TranscriptEntry
import com.randomwalk.aira.data.repository.CallsRepository
import com.randomwalk.aira.ui.nav.Destination
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CallDetailUiState(
    val isLoading: Boolean = true,
    val call: CallDetail? = null,
    val transcripts: List<TranscriptEntry> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class CallDetailViewModel @Inject constructor(
    private val repository: CallsRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val sessionId: String = checkNotNull(savedStateHandle[Destination.CallDetail.ARG_SESSION_ID])

    private val _uiState = MutableStateFlow(CallDetailUiState())
    val uiState: StateFlow<CallDetailUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            runCatching {
                coroutineScope {
                    val callDeferred = async { repository.getCall(sessionId) }
                    val transcriptsDeferred = async { repository.getTranscripts(sessionId) }
                    callDeferred.await() to transcriptsDeferred.await()
                }
            }.onSuccess { (call, transcripts) ->
                _uiState.value = CallDetailUiState(isLoading = false, call = call, transcripts = transcripts)
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message ?: "Failed to load call")
            }
        }
    }
}
