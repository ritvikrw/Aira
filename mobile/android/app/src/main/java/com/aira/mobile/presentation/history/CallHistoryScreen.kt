package com.aira.mobile.presentation.history

import android.text.format.DateFormat
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import android.content.Context
import com.aira.mobile.data.source.local.CallDatabaseHelper
import com.aira.mobile.data.source.local.CallLogEntity
import com.aira.mobile.data.source.local.TranscriptEntity
import com.aira.mobile.domain.repository.AgentRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Calendar
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CallHistoryScreen(
    dbHelper: CallDatabaseHelper,
    agentRepository: AgentRepository,
    onNavigateBack: () -> Unit
) {
    var callLogs by remember { mutableStateOf<List<CallLogEntity>>(emptyList()) }
    var selectedLogForTranscript by remember { mutableStateOf<CallLogEntity?>(null) }
    var transcriptsForSelectedLog by remember { mutableStateOf<List<TranscriptEntity>>(emptyList()) }
    var showTranscriptDialog by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(true) }
    var selectedTabState by remember { mutableStateOf(0) }

    val context = LocalContext.current
    val sharedPreferences = remember { context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE) }
    val scope = rememberCoroutineScope()

    val serverUrl = remember { sharedPreferences.getString("server_url", "wss://web-ninaiv-production-c6ae.up.railway.app/ws") ?: "wss://web-ninaiv-production-c6ae.up.railway.app/ws" }
    val httpUrl = remember(serverUrl) {
        val scheme = if (serverUrl.startsWith("wss://")) "https://" else "http://"
        val noScheme = serverUrl.substringAfter("://").substringBefore("/ws").substringBefore("/")
        val host = noScheme.substringBefore(":")
        val portStr = noScheme.substringAfter(":", "")
        if (portStr.isNotEmpty()) {
            val httpPort = if (portStr == "8000") "8001" else portStr
            "$scheme$host:$httpPort"
        } else {
            "$scheme$host"
        }
    }

    // Load call logs: merge server + local SQLite, dedup by sessionId
    LaunchedEffect(Unit) {
        scope.launch(Dispatchers.IO) {
            val localLogs = dbHelper.getAllCallLogs()
            withContext(Dispatchers.Main) {
                callLogs = localLogs
                isLoading = false
            }
        }
        android.util.Log.i("CallHistoryScreen", "Syncing call history from: $httpUrl/calls")
        agentRepository.fetchCallHistory(httpUrl) { jsonArray ->
            if (jsonArray != null) {
                android.util.Log.i("CallHistoryScreen", "Successfully fetched ${jsonArray.length()} calls from server")
                val serverList = mutableListOf<CallLogEntity>()
                try {
                    val sdf = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                    for (i in 0 until jsonArray.length()) {
                        val obj = jsonArray.getJSONObject(i)
                        val startTimeStr = obj.optString("call_start_time")
                        val startTime = if (startTimeStr.isNotEmpty()) {
                            sdf.parse(startTimeStr.substringBefore("."))?.time ?: System.currentTimeMillis()
                        } else {
                            System.currentTimeMillis()
                        }
                        val endTimeStr = obj.optString("call_end_time")
                        val endTime = if (endTimeStr.isNotEmpty()) {
                            sdf.parse(endTimeStr.substringBefore("."))?.time ?: System.currentTimeMillis()
                        } else {
                            System.currentTimeMillis()
                        }
                        serverList.add(
                            CallLogEntity(
                                sessionId = obj.optString("session_id"),
                                callerNumber = obj.optString("caller_phone"),
                                callerName = obj.optString("caller_name"),
                                status = obj.optString("status"),
                                startTime = startTime,
                                endTime = endTime,
                                durationSeconds = obj.optInt("call_duration_seconds"),
                                isSimulation = obj.optBoolean("is_simulation", false),
                                ttftMs = obj.optInt("llm_ttft_ms", 0),
                                totalLatencyMs = obj.optInt("total_latency_ms", 0),
                                summaryText = obj.optString("summary_text", "")
                            )
                        )
                    }
                    // Merge: server wins on duplicates, add local-only entries
                    val serverIds = serverList.map { it.sessionId }.toSet()
                    val localOnly = callLogs.filter { it.sessionId !in serverIds }
                    callLogs = (serverList + localOnly).sortedByDescending { it.startTime }
                    android.util.Log.i("CallHistoryScreen", "Call history merged. Total list size: ${callLogs.size}")
                } catch (e: Exception) {
                    android.util.Log.e("CallHistoryScreen", "Error merging call history: ${e.message}", e)
                }
            } else {
                android.util.Log.e("CallHistoryScreen", "Server call history fetch returned null")
            }
        }
    }

    // Load transcripts and latest summary when a log is selected
    LaunchedEffect(selectedLogForTranscript?.sessionId) {
        selectedLogForTranscript?.let { log ->
            val client = okhttp3.OkHttpClient()

            // Fetch latest summary from server (since background summarization takes a few seconds)
            val detailUrl = "$httpUrl/calls/${log.sessionId}"
            val detailRequest = okhttp3.Request.Builder().url(detailUrl).build()
            client.newCall(detailRequest).enqueue(object : okhttp3.Callback {
                override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {}
                override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                    response.use {
                        if (response.isSuccessful) {
                            try {
                                val bodyString = response.body?.string() ?: ""
                                if (bodyString.isNotEmpty()) {
                                    val obj = org.json.JSONObject(bodyString)
                                    val summaryText = obj.optString("summary_text", "")
                                    if (summaryText.isNotEmpty()) {
                                        selectedLogForTranscript = log.copy(summaryText = summaryText)
                                    }
                                }
                            } catch (_: Exception) {}
                        }
                    }
                }
            })

            // Try loading transcripts from server, fallback to SQLite
            val transcriptsUrl = "$httpUrl/transcripts/${log.sessionId}"
            val request = okhttp3.Request.Builder().url(transcriptsUrl).build()
            client.newCall(request).enqueue(object : okhttp3.Callback {
                override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                    scope.launch(Dispatchers.IO) {
                        transcriptsForSelectedLog = dbHelper.getTranscriptsForSession(log.sessionId)
                        showTranscriptDialog = true
                    }
                }

                override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                    response.use {
                        if (response.isSuccessful) {
                            try {
                                val bodyString = response.body?.string() ?: "[]"
                                val jsonArr = org.json.JSONArray(bodyString)
                                val list = mutableListOf<TranscriptEntity>()
                                for (i in 0 until jsonArr.length()) {
                                    val obj = jsonArr.getJSONObject(i)
                                    list.add(
                                        TranscriptEntity(
                                            sessionId = log.sessionId,
                                            speaker = obj.optString("speaker"),
                                            message = obj.optString("message"),
                                            timestamp = System.currentTimeMillis()
                                        )
                                    )
                                }
                                if (list.isEmpty()) {
                                    scope.launch(Dispatchers.IO) {
                                        transcriptsForSelectedLog = dbHelper.getTranscriptsForSession(log.sessionId)
                                        showTranscriptDialog = true
                                    }
                                } else {
                                    transcriptsForSelectedLog = list
                                    showTranscriptDialog = true
                                }
                            } catch (e: Exception) {
                                scope.launch(Dispatchers.IO) {
                                    transcriptsForSelectedLog = dbHelper.getTranscriptsForSession(log.sessionId)
                                    showTranscriptDialog = true
                                }
                            }
                        } else {
                            scope.launch(Dispatchers.IO) {
                                transcriptsForSelectedLog = dbHelper.getTranscriptsForSession(log.sessionId)
                                showTranscriptDialog = true
                            }
                        }
                    }
                }
            })
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF1A1B2F),
                        Color(0xFF12131C)
                    )
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onNavigateBack,
                    colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF2C2D4A))
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = Color.White
                    )
                }

                Spacer(modifier = Modifier.width(16.dp))

                Column {
                    Text(
                        text = "Call Logs",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Review AI receptionist conversation history",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Tab selection: All Calls / Simulated Only
            TabRow(
                selectedTabIndex = selectedTabState,
                containerColor = Color(0xFF1E1F35),
                contentColor = Color.White,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp)
                    .clip(RoundedCornerShape(10.dp))
            ) {
                Tab(
                    selected = selectedTabState == 0,
                    onClick = { selectedTabState = 0 },
                    text = { Text("All Calls", fontWeight = FontWeight.Bold, fontSize = 14.sp) }
                )
                Tab(
                    selected = selectedTabState == 1,
                    onClick = { selectedTabState = 1 },
                    text = { Text("Simulated Only", fontWeight = FontWeight.Bold, fontSize = 14.sp) }
                )
            }

            val filteredCallLogs = remember(callLogs, selectedTabState) {
                callLogs.filter { log ->
                    if (selectedTabState == 0) true else log.isSimulation
                }
            }

            if (isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color(0xFF5A6BFA))
                }
            } else if (filteredCallLogs.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = Color(0xFF8A9AFA).copy(alpha = 0.5f),
                        modifier = Modifier.size(64.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "No call logs found",
                        color = Color.Gray,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = if (selectedTabState == 0) "No calls yet — real or simulated calls handled by AIRA appear here" else "Simulated calls run for testing will appear here",
                        color = Color.DarkGray,
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(horizontal = 32.dp, vertical = 8.dp)
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredCallLogs) { log ->
                        CallLogItem(
                            log = log,
                            onClick = { selectedLogForTranscript = log }
                        )
                    }
                }
            }
        }

        // Transcript Dialog
        if (showTranscriptDialog && selectedLogForTranscript != null) {
            val context = LocalContext.current
            TranscriptViewerDialog(
                log = selectedLogForTranscript!!,
                transcripts = transcriptsForSelectedLog,
                onFlagMessage = { trans ->
                    flagResponse(context, selectedLogForTranscript!!, trans)
                },
                onDismiss = {
                    showTranscriptDialog = false
                    selectedLogForTranscript = null
                    transcriptsForSelectedLog = emptyList()
                }
            )
        }
    }
}

@Composable
fun CallLogItem(
    log: CallLogEntity,
    onClick: () -> Unit
) {
    val formattedTime = remember(log.startTime) {
        val cal = Calendar.getInstance().apply { timeInMillis = log.startTime }
        DateFormat.format("dd MMM yyyy, hh:mm a", cal).toString()
    }

    val durationText = remember(log.durationSeconds) {
        if (log.durationSeconds <= 0) {
            "Ringing / Missed"
        } else {
            val mins = log.durationSeconds / 60
            val secs = log.durationSeconds % 60
            if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
        }
    }

    val statusColor = when (log.status.lowercase(Locale.ROOT)) {
        "completed" -> Color(0xFF4CAF50)
        "active" -> Color(0xFFFFC107)
        "rejected" -> Color(0xFFE91E63)
        else -> Color.Gray
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(Color(0xFF2C2D4A), RoundedCornerShape(20.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Person,
                    contentDescription = null,
                    tint = Color(0xFF8A9AFA)
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = if (log.callerName.isNotEmpty() && log.callerName != "Incoming Call") log.callerName else log.callerNumber,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
                Text(
                    text = formattedTime,
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                if (log.ttftMs > 0 || log.totalLatencyMs > 0) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (log.ttftMs > 0) {
                            Text(
                                text = "TTFT: ${log.ttftMs}ms",
                                color = Color(0xFF8A9AFA),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        if (log.totalLatencyMs > 0) {
                            Text(
                                text = "Total: ${log.totalLatencyMs}ms",
                                color = Color(0xFF4CAF50),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }

            Column(
                horizontalAlignment = Alignment.End
            ) {
                if (log.isSimulation) {
                    Text(
                        text = "SIM",
                        color = Color(0xFF5A6BFA),
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 10.sp
                    )
                }
                Text(
                    text = durationText,
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
                Text(
                    text = log.status.uppercase(Locale.ROOT),
                    color = statusColor,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 10.sp
                )
            }
        }
    }
}

@Composable
fun TranscriptViewerDialog(
    log: CallLogEntity,
    transcripts: List<TranscriptEntity>,
    onFlagMessage: (TranscriptEntity) -> Unit,
    onDismiss: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.8f)
                .padding(vertical = 16.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(20.dp)
            ) {
                Text(
                    text = "Transcript: ${log.callerNumber}",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp
                )
                Text(
                    text = "Conversation history for this call session",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                
                if (log.ttftMs > 0 || log.totalLatencyMs > 0) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (log.ttftMs > 0) {
                            Text(
                                text = "Avg TTFT: ${log.ttftMs}ms",
                                color = Color(0xFF8A9AFA),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        if (log.totalLatencyMs > 0) {
                            Text(
                                text = "Avg Turn Gen: ${log.totalLatencyMs}ms",
                                color = Color(0xFF4CAF50),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                if (log.summaryText.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Surface(
                        color = Color(0xFF2C2D4A).copy(alpha = 0.5f),
                        shape = RoundedCornerShape(12.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF5A6BFA).copy(alpha = 0.3f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = "AI Summary",
                                    color = Color(0xFF8A9AFA),
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "🪄",
                                    fontSize = 12.sp
                                )
                            }
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = log.summaryText,
                                color = Color.White.copy(alpha = 0.9f),
                                fontSize = 13.sp,
                                lineHeight = 18.sp
                            )
                        }
                    }
                }
                
                HorizontalDivider(
                    color = Color(0xFF2C2D4A),
                    modifier = Modifier.padding(vertical = 12.dp)
                )

                if (transcripts.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No dialogue recorded for this call",
                            color = Color.Gray,
                            fontSize = 14.sp,
                            textAlign = TextAlign.Center
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(transcripts) { trans ->
                            TranscriptBubble(trans = trans, onFlag = onFlagMessage)
                        }
                    }
                }

                HorizontalDivider(
                    color = Color(0xFF2C2D4A),
                    modifier = Modifier.padding(vertical = 12.dp)
                )

                Button(
                    onClick = onDismiss,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA)),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                ) {
                    Text("Close Details", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
fun TranscriptBubble(trans: TranscriptEntity, onFlag: (TranscriptEntity) -> Unit) {
    val isUser = trans.speaker.lowercase(Locale.ROOT) == "user"
    val isSystem = trans.speaker.lowercase(Locale.ROOT) == "system"
    
    val bubbleColor = when {
        isUser -> Color(0xFF5A6BFA).copy(alpha = 0.2f)
        isSystem -> Color(0xFFE91E63).copy(alpha = 0.1f)
        else -> Color(0xFF2C2D4A)
    }
    
    val textColor = when {
        isSystem -> Color(0xFFE91E63)
        else -> Color.White
    }

    val bubbleAlignment = if (isUser) Alignment.End else Alignment.Start

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = bubbleAlignment
    ) {
        Text(
            text = trans.speaker.uppercase(Locale.ROOT),
            color = Color.Gray,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (isUser) {
                Spacer(modifier = Modifier.weight(1f))
                Surface(
                    color = bubbleColor,
                    shape = RoundedCornerShape(
                        topStart = 12.dp,
                        topEnd = 12.dp,
                        bottomStart = 12.dp,
                        bottomEnd = 0.dp
                    ),
                    modifier = Modifier.widthIn(max = 240.dp)
                ) {
                    Text(
                        text = trans.message,
                        color = textColor,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            } else {
                Surface(
                    color = bubbleColor,
                    shape = RoundedCornerShape(
                        topStart = 12.dp,
                        topEnd = 12.dp,
                        bottomStart = 0.dp,
                        bottomEnd = 12.dp
                    ),
                    modifier = Modifier.widthIn(max = 220.dp)
                ) {
                    Text(
                        text = trans.message,
                        color = textColor,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(12.dp)
                    )
                }
                
                if (!isSystem) {
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = { onFlag(trans) },
                        modifier = Modifier.size(28.dp)
                    ) {
                        Text(text = "🚩", fontSize = 14.sp)
                    }
                }
                Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

private fun flagResponse(context: android.content.Context, log: CallLogEntity, trans: TranscriptEntity) {
    try {
        val dir = context.getExternalFilesDir(null)
        val file = java.io.File(dir, "flagged_responses.txt")
        java.io.FileWriter(file, true).use { writer ->
            val timestamp = android.text.format.DateFormat.format("yyyy-MM-dd HH:mm:ss", java.util.Calendar.getInstance())
            writer.append("=========================================\n")
            writer.append("FLAGGED RESPONSE AT: $timestamp\n")
            writer.append("Session ID: ${log.sessionId}\n")
            writer.append("Caller Number: ${log.callerNumber}\n")
            writer.append("Caller Name: ${log.callerName}\n")
            writer.append("Message ID: ${trans.id}\n")
            writer.append("Speaker: ${trans.speaker}\n")
            writer.append("Flagged Message: ${trans.message}\n")
            writer.append("=========================================\n\n")
        }
        android.widget.Toast.makeText(context, "Response flagged and saved to flagged_responses.txt", android.widget.Toast.LENGTH_SHORT).show()
    } catch (e: Exception) {
        android.util.Log.e("CallHistoryScreen", "Failed to flag response", e)
        android.widget.Toast.makeText(context, "Failed to flag: ${e.message}", android.widget.Toast.LENGTH_SHORT).show()
    }
}
