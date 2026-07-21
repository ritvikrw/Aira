package com.aira.mobile.service

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.os.Build
import android.telecom.Connection
import android.telecom.DisconnectCause
import android.util.Log
import androidx.core.content.ContextCompat
import com.aira.mobile.data.source.local.CallDatabaseHelper
import com.aira.mobile.data.source.local.CallLogEntity
import com.aira.mobile.data.source.local.TranscriptEntity
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONObject
import java.util.UUID
import kotlin.concurrent.thread

class MyConnection(private val context: Context) : Connection() {
    companion object {
        private const val TAG = "MyConnection"
    }

    private var isRunning = false
    private var isCallActive = false
    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 3
    private var audioRecord: AudioRecord? = null
    private var audioTrack: AudioTrack? = null
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()
    private val dbHelper = CallDatabaseHelper(context)
    private val sessionId = UUID.randomUUID().toString()
    private var callStartTime = 0L
    private var originalAudioMode = AudioManager.MODE_NORMAL
    private var originalSpeakerphoneState = false
    
    private var isSimulation = false
    private var customCallerName = "Incoming Call"

    fun setSimulation(sim: Boolean) {
        this.isSimulation = sim
    }

    fun setCallerName(name: String) {
        this.customCallerName = name
    }

    fun initializingCall() {
        val sharedPreferences = context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE)
        val isEnabled = sharedPreferences.getBoolean("agent_enabled", false)
        if (!isEnabled) {
            Log.i(TAG, "AI Receptionist is disabled. Not initializing call, logging or WebSocket.")
            setDisconnected(DisconnectCause(DisconnectCause.CANCELED))
            destroy()
            return
        }

        Log.i(TAG, "initializingCall: Setting self-managed connection property and setting active")
        connectionProperties = PROPERTY_SELF_MANAGED
        // Automatically answer the call when it arrives
        setActive()
        
        isCallActive = true
        MyConnectionService.startForeground("Active call with " + (address?.schemeSpecificPart ?: "Unknown"))
        
        // Log call initialization in DB
        callStartTime = System.currentTimeMillis()
        val callerNum = address?.schemeSpecificPart ?: "Unknown"
        dbHelper.insertCallLog(
            CallLogEntity(
                sessionId = sessionId,
                callerNumber = callerNum,
                callerName = customCallerName,
                status = "ringing",
                startTime = callStartTime,
                isSimulation = isSimulation
            )
        )
        
        connectToWebSocket()
    }

    override fun onAnswer() {
        val sharedPreferences = context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE)
        val isEnabled = sharedPreferences.getBoolean("agent_enabled", false)
        if (!isEnabled) {
            Log.i(TAG, "AI Receptionist is disabled. Ignoring onAnswer.")
            setDisconnected(DisconnectCause(DisconnectCause.CANCELED))
            destroy()
            return
        }

        super.onAnswer()
        Log.i(TAG, "onAnswer called")
        setActive()
        
        isCallActive = true
        MyConnectionService.startForeground("Active call with " + (address?.schemeSpecificPart ?: "Unknown"))
        
        // Update DB status to active
        dbHelper.insertCallLog(
            CallLogEntity(
                sessionId = sessionId,
                callerNumber = address?.schemeSpecificPart ?: "Unknown",
                callerName = customCallerName,
                status = "active",
                startTime = callStartTime,
                isSimulation = isSimulation
            )
        )
        
        connectToWebSocket()
    }

    override fun onDisconnect() {
        super.onDisconnect()
        Log.i(TAG, "onDisconnect called")
        cleanup()
        
        val endTime = System.currentTimeMillis()
        val duration = ((endTime - callStartTime) / 1000).toInt()
        dbHelper.updateCallEnd(sessionId, endTime, duration, "completed")
        
        setDisconnected(DisconnectCause(DisconnectCause.LOCAL))
        destroy()
    }

    override fun onReject() {
        super.onReject()
        Log.i(TAG, "onReject called")
        cleanup()
        
        val endTime = System.currentTimeMillis()
        val duration = ((endTime - callStartTime) / 1000).toInt()
        dbHelper.updateCallEnd(sessionId, endTime, duration, "rejected")
        
        setDisconnected(DisconnectCause(DisconnectCause.REJECTED))
        destroy()
    }

    @Synchronized
    private fun connectToWebSocket() {
        if (webSocket != null) {
            Log.w(TAG, "connectToWebSocket: WebSocket connection already active")
            return
        }
        if (!isCallActive) {
            Log.w(TAG, "connectToWebSocket: Call is not active, ignoring connection request")
            return
        }

        val sharedPreferences = context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE)
        val serverUrl = sharedPreferences.getString("server_url", "wss://web-ninaiv-production-c6ae.up.railway.app/ws") ?: "wss://web-ninaiv-production-c6ae.up.railway.app/ws"
        val callerNum = address?.schemeSpecificPart ?: "Unknown"

        if (callerNum == "5550199" || serverUrl.trim().lowercase() == "echo" || serverUrl.trim().lowercase() == "ws://echo") {
            Log.i(TAG, "Running in local echo loop mode (test number or echo URL)")
            startLocalEchoLoop()
            return
        }

        val isSim = isSimulation || callerNum == "12345"
        val simulationPrompt = sharedPreferences.getString("simulation_prompt", "") ?: ""
        val cleanNumber = callerNum.replace(Regex("[^0-9+]"), "")
        var wsUrl = if (serverUrl.contains("?")) {
            "$serverUrl&session_id=$sessionId&caller_phone=$cleanNumber"
        } else {
            "$serverUrl?session_id=$sessionId&caller_phone=$cleanNumber"
        }

        if (isSim) {
            wsUrl += "&is_simulation=true"
            if (simulationPrompt.isNotEmpty()) {
                val encodedPrompt = java.net.URLEncoder.encode(simulationPrompt, "UTF-8")
                wsUrl += "&simulation_prompt=$encodedPrompt"
            }
        }
        Log.i(TAG, "Connecting to Pipecat WebSocket: $wsUrl")

        val request = Request.Builder().url(wsUrl).build()
        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "WebSocket Connected successfully to Pipecat Backend")
                reconnectAttempts = 0
                this@MyConnection.webSocket = webSocket
                if (!isRunning) {
                    startAudioLoop(webSocket)
                }
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                // Play synthesized audio packet received from Pipecat
                val audioData = bytes.toByteArray()
                audioTrack?.write(audioData, 0, audioData.size)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.i(TAG, "Received message: $text")
                try {
                    val json = JSONObject(text)
                    val msgType = json.optString("type")
                    if (msgType == "transcript") {
                        val speaker = json.optString("speaker")
                        val message = json.optString("text")
                        dbHelper.insertTranscript(
                            TranscriptEntity(
                                sessionId = sessionId,
                                speaker = speaker,
                                message = message,
                                timestamp = System.currentTimeMillis()
                            )
                        )
                    } else if (msgType == "metrics") {
                        val ttft = json.optInt("llm_ttft_ms", 0)
                        val totalTurn = json.optInt("total_turn_ms", 0)
                        if (ttft > 0 || totalTurn > 0) {
                            dbHelper.updateCallMetrics(sessionId, ttft, totalTurn)
                        }
                    } else if (msgType == "interrupted") {
                        Log.i(TAG, "Interruption received, stopping current audio playback")
                        stopAudioPlayback()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse text message JSON", e)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket connection failure: ${t.message}", t)
                
                dbHelper.insertTranscript(
                    TranscriptEntity(
                        sessionId = sessionId,
                        speaker = "system",
                        message = "[System error: Connection to AI backend failed - ${t.message}]",
                        timestamp = System.currentTimeMillis()
                    )
                )
                
                retryConnection()
            }
        }
        webSocket = client.newWebSocket(request, listener)
    }

    private fun startAudioLoop(ws: WebSocket) {
        // Verify microphone permission before recording
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Cannot start audio loop: RECORD_AUDIO permission is not granted.")
            return
        }

        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        originalAudioMode = audioManager.mode
        originalSpeakerphoneState = audioManager.isSpeakerphoneOn

        // Set mode to IN_COMMUNICATION for call audio optimization
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        setSpeakerphoneEnabled(audioManager, true)

        val sampleRate = 16000
        val channelConfigIn = AudioFormat.CHANNEL_IN_MONO
        val channelConfigOut = AudioFormat.CHANNEL_OUT_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfigIn, audioFormat)

        if (bufferSize <= 0) {
            Log.e(TAG, "Invalid buffer size: $bufferSize")
            return
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate,
                channelConfigIn,
                audioFormat,
                bufferSize
            )

            audioTrack = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setLegacyStreamType(AudioManager.STREAM_VOICE_CALL)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(audioFormat)
                        .setSampleRate(sampleRate)
                        .setChannelMask(channelConfigOut)
                        .build()
                )
                .setBufferSizeInBytes(bufferSize)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize")
                return
            }

            if (audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
                Log.e(TAG, "AudioTrack failed to initialize")
                return
            }

            isRunning = true
            audioRecord?.startRecording()
            audioTrack?.play()

            // Background thread to record and stream audio to WebSocket
            thread(start = true, name = "AudioRecordThread") {
                val buffer = ByteArray(bufferSize)
                Log.i(TAG, "Audio Record thread started, streaming mic input to WS")
                while (isRunning) {
                    val readBytes = audioRecord?.read(buffer, 0, bufferSize) ?: 0
                    if (readBytes > 0 && isRunning) {
                        val frame = buffer.copyOfRange(0, readBytes)
                        this@MyConnection.webSocket?.send(ByteString.of(*frame))
                    }
                }
                Log.i(TAG, "Audio Record thread stopped")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error setting up WebSocket audio streaming", e)
            cleanup()
        }
    }

    private fun retryConnection() {
        if (!isCallActive) {
            Log.i(TAG, "retryConnection: Call is no longer active, stopping retry.")
            return
        }

        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++
            Log.i(TAG, "Attempting socket reconnect: $reconnectAttempts/$maxReconnectAttempts")
            
            // Clean up the old WebSocket before reconnecting
            webSocket?.close(1000, "Reconnecting")
            webSocket = null

            // Wait 2 seconds before retry on a separate thread
            thread(start = true, name = "ReconnectThread") {
                try {
                    Thread.sleep(2000)
                    if (isCallActive) {
                        connectToWebSocket()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error during reconnect sleep", e)
                }
            }
        } else {
            Log.e(TAG, "Max reconnect attempts reached. Playing local fallback audio.")
            playLocalFallbackAudio()
        }
    }

    private fun playLocalFallbackAudio() {
        Log.i(TAG, "Playing local fallback audio...")
        
        // Ensure isRunning is set to false to stop recording loop
        isRunning = false
        
        // Stop and release old WebSocket if any
        webSocket?.close(1000, "Reconnecting failed")
        webSocket = null
        
        thread(start = true, name = "FallbackAudioThread") {
            var track: AudioTrack? = null
            try {
                val sampleRate = 16000
                val channelConfigOut = AudioFormat.CHANNEL_OUT_MONO
                val audioFormat = AudioFormat.ENCODING_PCM_16BIT
                val bufferSize = AudioTrack.getMinBufferSize(sampleRate, channelConfigOut, audioFormat)
                
                track = audioTrack ?: AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setLegacyStreamType(AudioManager.STREAM_VOICE_CALL)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(audioFormat)
                            .setSampleRate(sampleRate)
                            .setChannelMask(channelConfigOut)
                            .build()
                    )
                    .setBufferSizeInBytes(bufferSize)
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()

                if (track.state != AudioTrack.STATE_INITIALIZED) {
                    Log.e(TAG, "Fallback AudioTrack not initialized")
                    onDisconnect()
                    return@thread
                }

                track.play()

                // Open the asset file and stream it to the AudioTrack
                context.assets.open("fallback_error.pcm").use { inputStream ->
                    val buffer = ByteArray(4096)
                    var bytesRead = inputStream.read(buffer)
                    while (bytesRead != -1 && isCallActive) {
                        track.write(buffer, 0, bytesRead)
                        bytesRead = inputStream.read(buffer)
                    }
                }
                
                // Let the track finish playing before disconnecting
                Thread.sleep(1000)
                
            } catch (e: Exception) {
                Log.e(TAG, "Error playing fallback audio", e)
            } finally {
                try {
                    track?.stop()
                    track?.release()
                } catch (e: Exception) {
                    Log.e(TAG, "Error releasing fallback AudioTrack", e)
                }
                if (track == audioTrack) {
                    audioTrack = null
                }
                
                // Finally disconnect the call gracefully
                Log.i(TAG, "Fallback audio finished, disconnecting call.")
                onDisconnect()
            }
        }
    }

    private fun startLocalEchoLoop() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Cannot start local echo: RECORD_AUDIO permission is not granted.")
            return
        }

        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        originalAudioMode = audioManager.mode
        originalSpeakerphoneState = audioManager.isSpeakerphoneOn

        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        setSpeakerphoneEnabled(audioManager, true)

        val sampleRate = 16000
        val channelConfigIn = AudioFormat.CHANNEL_IN_MONO
        val channelConfigOut = AudioFormat.CHANNEL_OUT_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfigIn, audioFormat)

        if (bufferSize <= 0) {
            Log.e(TAG, "Invalid buffer size: $bufferSize")
            return
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate,
                channelConfigIn,
                audioFormat,
                bufferSize
            )

            audioTrack = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setLegacyStreamType(AudioManager.STREAM_VOICE_CALL)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(audioFormat)
                        .setSampleRate(sampleRate)
                        .setChannelMask(channelConfigOut)
                        .build()
                )
                .setBufferSizeInBytes(bufferSize)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED || audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord or AudioTrack failed to initialize for local echo")
                cleanup()
                return
            }

            isRunning = true
            audioRecord?.startRecording()
            audioTrack?.play()

            dbHelper.insertTranscript(
                TranscriptEntity(
                    sessionId = sessionId,
                    speaker = "system",
                    message = "[Local Audio Echo Loop Active]",
                    timestamp = System.currentTimeMillis()
                )
            )

            thread(start = true, name = "LocalEchoThread") {
                val buffer = ByteArray(bufferSize)
                Log.i(TAG, "Local Echo thread started, echoing mic to speaker")
                while (isRunning) {
                    val readBytes = audioRecord?.read(buffer, 0, bufferSize) ?: 0
                    if (readBytes > 0 && isRunning) {
                        audioTrack?.write(buffer, 0, readBytes)
                    }
                }
                Log.i(TAG, "Local Echo thread stopped")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error setting up local echo loop", e)
            cleanup()
        }
    }

    private fun stopAudioPlayback() {
        try {
            audioTrack?.let { track ->
                if (track.state == AudioTrack.STATE_INITIALIZED) {
                    track.pause()
                    track.flush()
                    track.play()
                    Log.i(TAG, "AudioTrack play buffer cleared successfully")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping audio playback on interruption", e)
        }
    }

    private fun cleanup() {
        isRunning = false
        isCallActive = false
        MyConnectionService.stopForeground()

        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        try {
            audioManager.mode = originalAudioMode
            setSpeakerphoneEnabled(audioManager, false)
            Log.i(TAG, "Restored AudioManager mode to $originalAudioMode and cleared speakerphone")
        } catch (e: Exception) {
            Log.e(TAG, "Error restoring AudioManager state", e)
        }
        webSocket?.close(1000, "Call ended")
        webSocket = null
        try {
            audioRecord?.stop()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping audioRecord", e)
        } finally {
            audioRecord?.release()
            audioRecord = null
        }

        try {
            audioTrack?.stop()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping audioTrack", e)
        } finally {
            audioTrack?.release()
            audioTrack = null
        }
        Log.i(TAG, "Audio devices released successfully")
    }

    private fun setSpeakerphoneEnabled(audioManager: AudioManager, enable: Boolean) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (enable) {
                val devices = audioManager.availableCommunicationDevices
                val speakerDevice = devices.find { it.type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER }
                if (speakerDevice != null) {
                    val result = audioManager.setCommunicationDevice(speakerDevice)
                    Log.i(TAG, "setCommunicationDevice speakerphone result: $result")
                } else {
                    Log.w(TAG, "Built-in speaker device not found in available communication devices")
                }
            } else {
                audioManager.clearCommunicationDevice()
                Log.i(TAG, "clearCommunicationDevice speakerphone cleared")
            }
        } else {
            @Suppress("DEPRECATION")
            audioManager.isSpeakerphoneOn = enable
            Log.i(TAG, "Legacy setSpeakerphoneOn: $enable")
        }
    }
}
