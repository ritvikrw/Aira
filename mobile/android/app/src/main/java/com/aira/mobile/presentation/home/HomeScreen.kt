package com.aira.mobile.presentation.home

import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aira.mobile.domain.repository.AgentRepository
import com.aira.mobile.service.TelecomHelper
import com.aira.mobile.service.MyConnection

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    agentRepository: AgentRepository,
    onNavigateToPermissions: () -> Unit,
    onNavigateToConfig: () -> Unit,
    onNavigateToStatus: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToFallback: () -> Unit
) {
    val context = LocalContext.current
    val telecomHelper = remember { TelecomHelper(context) }
    val sharedPreferences = remember { context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE) }
    
    var agentEnabled by remember {
        mutableStateOf(sharedPreferences.getBoolean("agent_enabled", false))
    }
    
    var isDefaultDialer by remember { mutableStateOf(telecomHelper.isDefaultDialer()) }
    var isPhoneAccountRegistered by remember { mutableStateOf(telecomHelper.isPhoneAccountRegistered()) }
    val micVolume by remember { MyConnection.micVolume }
    val botSpeaking by remember { MyConnection.botSpeaking }
    val agentStatus by remember { MyConnection.agentStatus }
    val lastLlmTtftMs by remember { MyConnection.lastLlmTtftMs }
    val lastTotalTurnMs by remember { MyConnection.lastTotalTurnMs }
    val isCallActive by remember { MyConnection.isCallActive }

    var showSimulationDialog by remember { mutableStateOf(false) }
    // Simulation prompt is the same as Agent Config's custom_instructions — one source of truth
    var simulationPrompt by remember {
        mutableStateOf(sharedPreferences.getString("custom_instructions", "") ?: "")
    }
    
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

    // Refresh states periodically
    LaunchedEffect(Unit) {
        isDefaultDialer = telecomHelper.isDefaultDialer()
        isPhoneAccountRegistered = telecomHelper.isPhoneAccountRegistered()

        agentRepository.fetchSettings(httpUrl) { map ->
            if (map != null) {
                map["agent_enabled"]?.let {
                    val enabled = it == "true"
                    agentEnabled = enabled
                    sharedPreferences.edit().putBoolean("agent_enabled", enabled).apply()
                }
            }
        }
    }

    // Color animations
    val indicatorColor by animateColorAsState(
        targetValue = if (agentEnabled && isDefaultDialer) Color(0xFF4CAF50) else Color(0xFFE91E63),
        label = "statusColor"
    )

    // Pulse animation for status
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )
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
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "AIRA",
                        color = Color.White,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold
                    )
                    Text(
                        text = "AI Receptionist Agent",
                        color = Color(0xFF8A9AFA),
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

                IconButton(
                    onClick = onNavigateToPermissions,
                    colors = IconButtonDefaults.iconButtonColors(
                        containerColor = Color(0xFF2C2D4A)
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.Settings,
                        contentDescription = "Setup Checklist",
                        tint = Color.White
                    )
                }
            }

            // Scrollable Content Area
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(vertical = 12.dp)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Central Status Bubble
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier.size(160.dp)
                ) {
                    // Pulse ring
                    Box(
                        modifier = Modifier
                            .size(140.dp)
                            .scale(if (agentEnabled) pulseScale else 1.0f)
                            .clip(CircleShape)
                            .background(indicatorColor.copy(alpha = 0.15f))
                            .border(2.dp, indicatorColor.copy(alpha = 0.4f), CircleShape)
                    )
                    
                    // Main circle
                    Surface(
                        modifier = Modifier.size(110.dp),
                        shape = CircleShape,
                        color = Color(0xFF23243C),
                        tonalElevation = 8.dp
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center,
                            modifier = Modifier.fillMaxSize()
                        ) {
                            Text(
                                text = if (agentEnabled) "ACTIVE" else "MUTED",
                                color = indicatorColor,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
                
                val statusLabel = when {
                    !agentEnabled -> "Agent Muted"
                    agentStatus == MyConnection.Companion.AgentStatus.LISTENING -> "Listening..."
                    agentStatus == MyConnection.Companion.AgentStatus.PROCESSING -> "Processing..."
                    agentStatus == MyConnection.Companion.AgentStatus.SPEAKING -> "Speaking..."
                    else -> "Awaiting Incoming Calls..."
                }
                val statusColor = when {
                    !agentEnabled -> Color.Gray
                    agentStatus == MyConnection.Companion.AgentStatus.LISTENING -> Color(0xFF5A6BFA)
                    agentStatus == MyConnection.Companion.AgentStatus.PROCESSING -> Color(0xFFFFC107)
                    agentStatus == MyConnection.Companion.AgentStatus.SPEAKING -> Color(0xFF4CAF50)
                    else -> Color.White
                }
                Text(
                    text = statusLabel,
                    color = statusColor,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )

                if (agentEnabled) {
                    AudioWaveformVisualizer(
                        volume = micVolume,
                        isBotSpeaking = botSpeaking,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }

                // Agent Toggle Control
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF23243C)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(18.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "AI Call Handler Status",
                                color = Color.White,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = if (agentEnabled) "Auto-answering calls active" else "Calls will ring standard UI",
                                color = Color.Gray,
                                fontSize = 11.sp
                            )
                        }
                        
                        Switch(
                            checked = agentEnabled,
                            onCheckedChange = { value ->
                                agentEnabled = value
                                sharedPreferences.edit().putBoolean("agent_enabled", value).apply()
                                agentRepository.saveSettings(httpUrl, mapOf("agent_enabled" to value.toString())) { _ -> }
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = Color(0xFF5A6BFA),
                                uncheckedThumbColor = Color.Gray,
                                uncheckedTrackColor = Color(0xFF161622)
                            )
                        )
                    }
                }

                // Model info + latency panel
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1B2F)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = "AI Stack",
                            color = Color(0xFF8A9AFA),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("STT", color = Color.Gray, fontSize = 10.sp)
                                Text("Sarvam saarika:v2.5", color = Color.White, fontSize = 11.sp)
                            }
                            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("LLM", color = Color.Gray, fontSize = 10.sp)
                                Text("Groq llama-3.1-8b", color = Color.White, fontSize = 11.sp, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                            }
                            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                                Text("TTS", color = Color.Gray, fontSize = 10.sp)
                                Text("Cartesia Ramya", color = Color.White, fontSize = 11.sp, textAlign = androidx.compose.ui.text.style.TextAlign.End)
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        HorizontalDivider(color = Color(0xFF2C2D4A))
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text("LLM TTFT", color = Color.Gray, fontSize = 10.sp)
                                Text(
                                    text = if (lastLlmTtftMs > 0) "${lastLlmTtftMs}ms" else "—",
                                    color = if (lastLlmTtftMs == 0) Color.Gray
                                            else if (lastLlmTtftMs < 800) Color(0xFF4CAF50)
                                            else Color(0xFFFFC107),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text("Total Turn", color = Color.Gray, fontSize = 10.sp)
                                Text(
                                    text = if (lastTotalTurnMs > 0) "${lastTotalTurnMs}ms" else "—",
                                    color = if (lastTotalTurnMs == 0) Color.Gray
                                            else if (lastTotalTurnMs < 2000) Color(0xFF4CAF50)
                                            else Color(0xFFFFC107),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                }

                // Navigation Cards Grid (2x2)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToConfig() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Icon(Icons.Default.Edit, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Agent Config", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("Edit prompt & name", color = Color.Gray, fontSize = 10.sp)
                        }
                    }
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToStatus() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Icon(Icons.Default.Build, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Connection", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("Test WS server port", color = Color.Gray, fontSize = 10.sp)
                        }
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToHistory() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Icon(Icons.Default.List, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Call History", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("View transcripts", color = Color.Gray, fontSize = 10.sp)
                        }
                    }
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToFallback() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Icon(Icons.Default.Lock, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Safety Settings", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("Blacklists & DND", color = Color.Gray, fontSize = 10.sp)
                        }
                    }
                }

                // Telecom Integration Status Card
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Telecom Integration Status",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isDefaultDialer) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (isDefaultDialer) Color(0xFF4CAF50) else Color(0xFFFFC107),
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isDefaultDialer) "Default Phone Application: Yes" else "Default Phone Application: No",
                                color = Color.LightGray,
                                fontSize = 12.sp
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isPhoneAccountRegistered) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (isPhoneAccountRegistered) Color(0xFF4CAF50) else Color(0xFFFFC107),
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isPhoneAccountRegistered) "Telecom PhoneAccount: Registered" else "Telecom PhoneAccount: Missing",
                                color = Color.LightGray,
                                fontSize = 12.sp
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (isCallActive) {
                // End Call button — shown during active call
                Button(
                    onClick = { MyConnection.activeConnection?.onDisconnect() },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE53935)),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                ) {
                    Text(
                        text = "End Call",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.ExtraBold
                    )
                }
            } else {
                // Simulate button — shown when no call is active
                Button(
                    onClick = { showSimulationDialog = true },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA)),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.padding(end = 8.dp)
                    )
                    Text(
                        text = "Simulate Incoming Call",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Simulation Dialog
        if (showSimulationDialog) {
            AlertDialog(
                onDismissRequest = { showSimulationDialog = false },
                title = {
                    Text(
                        text = "Simulate Incoming Call",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                },
                text = {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            text = "Custom instructions for this call (same as Agent Config):",
                            color = Color.LightGray,
                            fontSize = 12.sp
                        )
                        OutlinedTextField(
                            value = simulationPrompt,
                            onValueChange = { simulationPrompt = it },
                            label = { Text("Agent Instructions") },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF5A6BFA),
                                unfocusedBorderColor = Color.Gray,
                                focusedLabelColor = Color(0xFF8A9AFA),
                                unfocusedLabelColor = Color.Gray
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            maxLines = 6
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            sharedPreferences.edit()
                                .putString("custom_instructions", simulationPrompt)
                                .apply()
                            agentRepository.saveSettings(
                                httpUrl,
                                mapOf("custom_instructions" to simulationPrompt)
                            ) { _ -> }
                            telecomHelper.simulateIncomingCall(
                                callerName = "Test Caller (Simulation)",
                                callerNumber = "12345"
                            )
                            showSimulationDialog = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA))
                    ) {
                        Text("Start Call", fontWeight = FontWeight.Bold)
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showSimulationDialog = false }) {
                        Text("Cancel", color = Color.Gray)
                    }
                },
                containerColor = Color(0xFF1E1F35),
                shape = RoundedCornerShape(20.dp)
            )
        }
    }
}

@Composable
fun AudioWaveformVisualizer(
    volume: Float,
    isBotSpeaking: Boolean,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        val barCount = 7
        val baseHeights = listOf(12.dp, 24.dp, 36.dp, 48.dp, 36.dp, 24.dp, 12.dp)
        
        for (i in 0 until barCount) {
            val baseHeight = baseHeights[i]
            val targetHeight = if (isBotSpeaking) {
                val infiniteTransition = rememberInfiniteTransition(label = "bar_$i")
                val heightAnim by infiniteTransition.animateFloat(
                    initialValue = 8f,
                    targetValue = 28f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(400 + i * 100),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "heightAnim"
                )
                heightAnim.dp
            } else {
                (8.dp + baseHeight * volume * 2.5f).coerceAtMost(56.dp)
            }
            
            val color = if (isBotSpeaking) Color(0xFF4CAF50) else Color(0xFF5A6BFA)
            
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(targetHeight)
                    .background(color, RoundedCornerShape(2.dp))
            )
        }
    }
}
