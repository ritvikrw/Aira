package com.aira.mobile.data.source.remote

import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AgentApiService @Inject constructor(
    private val client: OkHttpClient
) {
    private var webSocket: WebSocket? = null

    fun connect(url: String, listener: WebSocketListener) {
        val request = Request.Builder().url(url).build()
        webSocket = client.newWebSocket(request, listener)
    }

    fun sendAudio(data: ByteArray): Boolean {
        val socket = webSocket ?: return false
        return socket.send(okio.ByteString.of(*data))
    }

    fun sendText(text: String): Boolean {
        val socket = webSocket ?: return false
        return socket.send(text)
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
    }

    fun fetchSettings(baseUrl: String, callback: (Map<String, String>?) -> Unit) {
        val request = Request.Builder()
            .url("$baseUrl/settings")
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(null)
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!response.isSuccessful) {
                        callback(null)
                        return
                    }
                    try {
                        val bodyString = response.body?.string() ?: "{}"
                        val json = JSONObject(bodyString)
                        val map = mutableMapOf<String, String>()
                        val keys = json.keys()
                        while (keys.hasNext()) {
                            val key = keys.next()
                            map[key] = json.optString(key)
                        }
                        callback(map)
                    } catch (e: Exception) {
                        callback(null)
                    }
                }
            }
        })
    }

    fun saveSettings(baseUrl: String, settings: Map<String, String>, callback: (Boolean) -> Unit) {
        val json = JSONObject()
        for ((key, value) in settings) {
            json.put(key, value)
        }
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val requestBody = json.toString().toRequestBody(mediaType)
        
        val request = Request.Builder()
            .url("$baseUrl/settings")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false)
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    callback(response.isSuccessful)
                }
            }
        })
    }

    fun fetchCallHistory(baseUrl: String, callback: (JSONArray?) -> Unit) {
        android.util.Log.i("AgentApiService", "fetchCallHistory: Fetching from $baseUrl/calls")
        val request = Request.Builder()
            .url("$baseUrl/calls")
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                android.util.Log.e("AgentApiService", "fetchCallHistory failed: ${e.message}", e)
                callback(null)
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    android.util.Log.i("AgentApiService", "fetchCallHistory response: code=${response.code}")
                    if (!response.isSuccessful) {
                        callback(null)
                        return
                    }
                    try {
                        val bodyString = response.body?.string() ?: "[]"
                        android.util.Log.i("AgentApiService", "fetchCallHistory body length: ${bodyString.length}")
                        val jsonArray = JSONArray(bodyString)
                        callback(jsonArray)
                    } catch (e: Exception) {
                        android.util.Log.e("AgentApiService", "fetchCallHistory parse error: ${e.message}", e)
                        callback(null)
                    }
                }
            }
        })
    }
}
