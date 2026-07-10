package com.randomwalk.aira.data.repository

import com.randomwalk.aira.data.network.AiraApiService
import com.randomwalk.aira.data.network.dto.CallDetail
import com.randomwalk.aira.data.network.dto.CallListItem
import com.randomwalk.aira.data.network.dto.CallTokenResponse
import com.randomwalk.aira.data.network.dto.TranscriptEntry
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CallsRepository @Inject constructor(private val api: AiraApiService) {

    suspend fun listCalls(): List<CallListItem> = api.listCalls()

    suspend fun getCall(sessionId: String): CallDetail = api.getCall(sessionId)

    suspend fun getTranscripts(sessionId: String): List<TranscriptEntry> = api.getTranscripts(sessionId)

    suspend fun createCallToken(): CallTokenResponse = api.createCallToken()

    suspend fun endCall(sessionId: String) = api.endCall(sessionId)
}
