package com.randomwalk.aira.data.network

import com.randomwalk.aira.data.network.dto.CallDetail
import com.randomwalk.aira.data.network.dto.CallListItem
import com.randomwalk.aira.data.network.dto.CallTokenResponse
import com.randomwalk.aira.data.network.dto.EndCallResponse
import com.randomwalk.aira.data.network.dto.TranscriptEntry
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface AiraApiService {

    @GET("calls/")
    suspend fun listCalls(): List<CallListItem>

    @GET("calls/{sessionId}")
    suspend fun getCall(@Path("sessionId") sessionId: String): CallDetail

    @GET("transcripts/{sessionId}")
    suspend fun getTranscripts(@Path("sessionId") sessionId: String): List<TranscriptEntry>

    @POST("calls/token")
    suspend fun createCallToken(): CallTokenResponse

    @POST("calls/{sessionId}/end")
    suspend fun endCall(@Path("sessionId") sessionId: String): EndCallResponse
}
