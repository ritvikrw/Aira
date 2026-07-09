package com.aira.mobile.presentation.config

import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aira.mobile.domain.repository.AgentRepository

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentConfigScreen(
    agentRepository: AgentRepository,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val sharedPreferences = remember { context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE) }

    var agentName by remember {
        mutableStateOf(sharedPreferences.getString("agent_name", "AIRA") ?: "AIRA")
    }
    var systemPrompt by remember {
        mutableStateOf(
            sharedPreferences.getString(
                "system_prompt",
                "You are AIRA, a prompt-based phone voice receptionist agent."
            ) ?: "You are AIRA, a prompt-based phone voice receptionist agent."
        )
    }
    var defaultLanguage by remember {
        mutableStateOf(sharedPreferences.getString("default_language", "en-IN") ?: "en-IN")
    }
    var agentEnabled by remember {
        mutableStateOf(sharedPreferences.getBoolean("agent_enabled", false))
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

    LaunchedEffect(Unit) {
        agentRepository.fetchSettings(httpUrl) { map ->
            if (map != null) {
                map["agent_name"]?.let { agentName = it }
                map["custom_instructions"]?.let { systemPrompt = it }
                map["default_language"]?.let { defaultLanguage = it }
                map["agent_enabled"]?.let {
                    val enabled = it == "true"
                    agentEnabled = enabled
                    sharedPreferences.edit().putBoolean("agent_enabled", enabled).apply()
                }
            }
        }
    }

    val languages = listOf(
        "en-IN" to "English (India)",
        "hi-IN" to "Hindi (India)",
        "te-IN" to "Telugu (India)",
        "ta-IN" to "Tamil (India)",
        "kn-IN" to "Kannada (India)",
        "ml-IN" to "Malayalam (India)"
    )

    var dropdownExpanded by remember { mutableStateOf(false) }

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
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Content Wrapper
            Column(modifier = Modifier.fillMaxWidth()) {
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
                            text = "Agent Configuration",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Customize agent personality and language",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // Name Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Agent Display Name",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = agentName,
                            onValueChange = { agentName = it },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF5A6BFA),
                                unfocusedBorderColor = Color(0xFF2C2D4A),
                                focusedContainerColor = Color(0xFF12131C),
                                unfocusedContainerColor = Color(0xFF12131C)
                            ),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                // Prompt Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "System Prompt / Instructions",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = systemPrompt,
                            onValueChange = { systemPrompt = it },
                            minLines = 4,
                            maxLines = 8,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF5A6BFA),
                                unfocusedBorderColor = Color(0xFF2C2D4A),
                                focusedContainerColor = Color(0xFF12131C),
                                unfocusedContainerColor = Color(0xFF12131C)
                            ),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                // Language Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Default Language",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        Box {
                            OutlinedTextField(
                                value = languages.find { it.first == defaultLanguage }?.second ?: defaultLanguage,
                                onValueChange = {},
                                readOnly = true,
                                trailingIcon = {
                                    Icon(
                                        imageVector = Icons.Default.ArrowDropDown,
                                        contentDescription = null,
                                        tint = Color.White
                                    )
                                },
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedTextColor = Color.White,
                                    unfocusedTextColor = Color.White,
                                    focusedBorderColor = Color(0xFF5A6BFA),
                                    unfocusedBorderColor = Color(0xFF2C2D4A),
                                    focusedContainerColor = Color(0xFF12131C),
                                    unfocusedContainerColor = Color(0xFF12131C)
                                ),
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { dropdownExpanded = true }
                            )
                            // Invisible overlay to trigger dropdown
                            Box(
                                modifier = Modifier
                                    .matchParentSize()
                                    .clickable { dropdownExpanded = true }
                            )

                            DropdownMenu(
                                expanded = dropdownExpanded,
                                onDismissRequest = { dropdownExpanded = false },
                                modifier = Modifier
                                    .background(Color(0xFF1E1F35))
                                    .fillMaxWidth(0.8f)
                            ) {
                                languages.forEach { (code, label) ->
                                    DropdownMenuItem(
                                        text = { Text(label, color = Color.White) },
                                        onClick = {
                                            defaultLanguage = code
                                            dropdownExpanded = false
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Save Button
            Button(
                onClick = {
                    sharedPreferences.edit().apply {
                        putString("agent_name", agentName)
                        putString("system_prompt", systemPrompt)
                        putString("default_language", defaultLanguage)
                        apply()
                    }
                    
                    val settingsMap = mapOf(
                        "agent_name" to agentName,
                        "custom_instructions" to systemPrompt,
                        "default_language" to defaultLanguage,
                        "agent_enabled" to agentEnabled.toString()
                    )
                    agentRepository.saveSettings(httpUrl, settingsMap) { success ->
                        // Background update completed
                    }
                    
                    Toast.makeText(context, "Settings saved!", Toast.LENGTH_SHORT).show()
                    onNavigateBack()
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA)),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Text(
                    text = "Save Configuration",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
