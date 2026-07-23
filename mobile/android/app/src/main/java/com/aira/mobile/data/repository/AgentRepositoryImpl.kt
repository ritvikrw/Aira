package com.aira.mobile.data.repository

import com.aira.mobile.data.source.remote.AgentApiService
import com.aira.mobile.domain.repository.AgentRepository
import okhttp3.WebSocketListener
import org.json.JSONArray
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AgentRepositoryImpl @Inject constructor(
    private val apiService: AgentApiService
) : AgentRepository {

    override fun connect(url: String, listener: WebSocketListener) {
        apiService.connect(url, listener)
    }

    override fun sendAudio(data: ByteArray): Boolean {
        return apiService.sendAudio(data)
    }

    override fun sendText(text: String): Boolean {
        return apiService.sendText(text)
    }

    override fun disconnect() {
        apiService.disconnect()
    }

    override fun fetchSettings(baseUrl: String, callback: (Map<String, String>?) -> Unit) {
        apiService.fetchSettings(baseUrl, callback)
    }

    override fun saveSettings(baseUrl: String, settings: Map<String, String>, callback: (Boolean) -> Unit) {
        apiService.saveSettings(baseUrl, settings, callback)
    }

    override fun fetchCallHistory(baseUrl: String, callback: (JSONArray?) -> Unit) {
        apiService.fetchCallHistory(baseUrl, callback)
    }

    override fun fetchAnalytics(baseUrl: String, callback: (org.json.JSONObject?) -> Unit) {
        apiService.fetchAnalytics(baseUrl, callback)
    }
}
