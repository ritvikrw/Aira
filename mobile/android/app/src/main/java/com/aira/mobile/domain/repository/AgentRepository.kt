package com.aira.mobile.domain.repository

import okhttp3.WebSocketListener
import org.json.JSONArray

interface AgentRepository {
    fun connect(url: String, listener: WebSocketListener)
    fun sendAudio(data: ByteArray): Boolean
    fun sendText(text: String): Boolean
    fun disconnect()
    fun fetchSettings(baseUrl: String, callback: (Map<String, String>?) -> Unit)
    fun saveSettings(baseUrl: String, settings: Map<String, String>, callback: (Boolean) -> Unit)
    fun fetchCallHistory(baseUrl: String, callback: (JSONArray?) -> Unit)
    fun fetchAnalytics(baseUrl: String, callback: (org.json.JSONObject?) -> Unit)
}
