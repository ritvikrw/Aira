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
    
    // Refresh states periodically
    LaunchedEffect(Unit) {
        isDefaultDialer = telecomHelper.isDefaultDialer()
        isPhoneAccountRegistered = telecomHelper.isPhoneAccountRegistered()
        
        val serverUrl = sharedPreferences.getString("server_url", "wss://web-ninaiv-production-c6ae.up.railway.app/ws") ?: "wss://web-ninaiv-production-c6ae.up.railway.app/ws"
        val scheme = if (serverUrl.startsWith("wss://")) "https://" else "http://"
        val noScheme = serverUrl.substringAfter("://").substringBefore("/ws").substringBefore("/")
        val host = noScheme.substringBefore(":")
        val portStr = noScheme.substringAfter(":", "")
        val httpUrl = if (portStr.isNotEmpty()) {
            val httpPort = if (portStr == "8000") "8001" else portStr
            "$scheme$host:$httpPort"
        } else {
            "$scheme$host"
        }
        
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

            // Central Status Bubble
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.weight(1f)
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier.size(200.dp)
                ) {
                    // Pulse ring
                    Box(
                        modifier = Modifier
                            .size(160.dp)
                            .scale(if (agentEnabled) pulseScale else 1.0f)
                            .clip(CircleShape)
                            .background(indicatorColor.copy(alpha = 0.15f))
                            .border(2.dp, indicatorColor.copy(alpha = 0.4f), CircleShape)
                    )
                    
                    // Main circle
                    Surface(
                        modifier = Modifier.size(120.dp),
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
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Text(
                    text = if (agentEnabled) "Awaiting Incoming Calls..." else "Agent Muted",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium
                )
            }

            // Controls & Metrics Card
            Column(
                modifier = Modifier.fillMaxWidth()
            ) {
                // Agent Toggle Control
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF23243C)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "AI Call Handler Status",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = if (agentEnabled) "Auto-answering calls active" else "Calls will ring standard UI",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                        
                        Switch(
                            checked = agentEnabled,
                            onCheckedChange = { value ->
                                agentEnabled = value
                                sharedPreferences.edit().putBoolean("agent_enabled", value).apply()
                                
                                val serverUrl = sharedPreferences.getString("server_url", "wss://web-ninaiv-production-c6ae.up.railway.app/ws") ?: "wss://web-ninaiv-production-c6ae.up.railway.app/ws"
                                val scheme = if (serverUrl.startsWith("wss://")) "https://" else "http://"
                                val noScheme = serverUrl.substringAfter("://").substringBefore("/ws").substringBefore("/")
                                val host = noScheme.substringBefore(":")
                                val portStr = noScheme.substringAfter(":", "")
                                val httpUrl = if (portStr.isNotEmpty()) {
                                    val httpPort = if (portStr == "8000") "8001" else portStr
                                    "$scheme$host:$httpPort"
                                } else {
                                    "$scheme$host"
                                }
                                
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

                // Navigation Cards Grid (2x2)
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToConfig() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Icon(Icons.Default.Edit, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Agent Config", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Edit prompt & name", color = Color.Gray, fontSize = 11.sp)
                        }
                    }
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToStatus() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Icon(Icons.Default.Build, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Connection", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Test WS server port", color = Color.Gray, fontSize = 11.sp)
                        }
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToHistory() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Icon(Icons.Default.List, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Call History", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("View transcripts", color = Color.Gray, fontSize = 11.sp)
                        }
                    }
                    Card(
                        modifier = Modifier.weight(1f).clickable { onNavigateToFallback() },
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35))
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Icon(Icons.Default.Lock, contentDescription = null, tint = Color(0xFF8A9AFA))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Safety Settings", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Blacklists & DND", color = Color.Gray, fontSize = 11.sp)
                        }
                    }
                }

                // Call Statistics / Setup Warnings Card
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(18.dp)
                    ) {
                        Text(
                            text = "Telecom Integration Status",
                            color = Color(0xFF8A9AFA),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        
                        // Default Dialer Check
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isDefaultDialer) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (isDefaultDialer) Color(0xFF4CAF50) else Color(0xFFFFC107),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isDefaultDialer) "Default Phone Application: Yes" else "Default Phone Application: No",
                                color = Color.LightGray,
                                fontSize = 13.sp
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        
                        // PhoneAccount Check
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isPhoneAccountRegistered) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (isPhoneAccountRegistered) Color(0xFF4CAF50) else Color(0xFFFFC107),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = if (isPhoneAccountRegistered) "Telecom PhoneAccount: Registered" else "Telecom PhoneAccount: Missing",
                                color = Color.LightGray,
                                fontSize = 13.sp
                            )
                        }
                    }
                }

                // Debug / Simulation Button
                Button(
                    onClick = {
                        telecomHelper.simulateIncomingCall(
                            callerName = "Test Call (Day 2)",
                            callerNumber = "12345"
                        )
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF5A6BFA)
                    ),
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
                        text = "Simulate Incoming Call (Audio Echo)",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}
