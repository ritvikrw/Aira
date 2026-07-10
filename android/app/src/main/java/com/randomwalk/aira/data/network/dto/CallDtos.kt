package com.randomwalk.aira.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CallSummaryOut(
    @SerialName("summary_text") val summaryText: String? = null,
    @SerialName("key_topics") val keyTopics: List<String> = emptyList(),
    @SerialName("action_items") val actionItems: List<String> = emptyList(),
    @SerialName("call_category") val callCategory: String? = null,
)

@Serializable
data class CallListItem(
    @SerialName("session_id") val sessionId: String,
    @SerialName("caller_id") val callerId: String? = null,
    @SerialName("caller_name") val callerName: String? = null,
    @SerialName("caller_phone") val callerPhone: String? = null,
    val status: String,
    @SerialName("call_start_time") val callStartTime: String? = null,
    @SerialName("call_duration_seconds") val callDurationSeconds: Int? = null,
    @SerialName("room_name") val roomName: String? = null,
    @SerialName("call_category") val callCategory: String? = null,
    @SerialName("summary_text") val summaryText: String? = null,
    @SerialName("key_topics") val keyTopics: List<String> = emptyList(),
    @SerialName("action_items") val actionItems: List<String> = emptyList(),
)

@Serializable
data class CallDetail(
    @SerialName("session_id") val sessionId: String,
    @SerialName("caller_id") val callerId: String? = null,
    @SerialName("caller_name") val callerName: String? = null,
    @SerialName("caller_phone") val callerPhone: String? = null,
    @SerialName("room_name") val roomName: String? = null,
    val status: String,
    @SerialName("call_start_time") val callStartTime: String? = null,
    @SerialName("call_end_time") val callEndTime: String? = null,
    @SerialName("call_duration_seconds") val callDurationSeconds: Int? = null,
    val summary: CallSummaryOut? = null,
)

@Serializable
data class TranscriptEntry(
    val id: Int,
    val speaker: String,
    val message: String,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class CallTokenResponse(
    @SerialName("server_url") val serverUrl: String,
    @SerialName("participant_token") val participantToken: String,
    @SerialName("room_name") val roomName: String,
)

@Serializable
data class EndCallResponse(
    @SerialName("session_id") val sessionId: String,
    @SerialName("duration_seconds") val durationSeconds: Int? = null,
)

@Serializable
data class StartCallRequest(
    @SerialName("session_id") val sessionId: String,
    @SerialName("caller_id") val callerId: String? = null,
    @SerialName("room_name") val roomName: String? = null,
)
