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

    var businessName by remember {
        mutableStateOf(sharedPreferences.getString("business_name", "Aira Solutions") ?: "Aira Solutions")
    }
    var agentName by remember {
        mutableStateOf(sharedPreferences.getString("agent_name", "Clara") ?: "Clara")
    }
    var businessHours by remember {
        mutableStateOf(sharedPreferences.getString("business_hours", "Monday to Friday, 9am to 6pm IST. Closed on weekends.") ?: "Monday to Friday, 9am to 6pm IST. Closed on weekends.")
    }
    var agentInstructions by remember {
        mutableStateOf(sharedPreferences.getString("agent_instructions", "Answer user queries, explain service offerings, and take callback requests politely.") ?: "Answer user queries, explain service offerings, and take callback requests politely.")
    }
    var topicsToAvoid by remember {
        mutableStateOf(sharedPreferences.getString("topics_to_avoid", "Competitor products, ongoing legal matters, internal pricing.") ?: "Competitor products, ongoing legal matters, internal pricing.")
    }
    var defaultLanguage by remember {
        mutableStateOf(sharedPreferences.getString("default_language", "en-IN") ?: "en-IN")
    }
    var agentEnabled by remember {
        mutableStateOf(sharedPreferences.getBoolean("agent_enabled", false))
    }

    val httpUrl = "https://web-ninaiv-production-c6ae.up.railway.app"

    LaunchedEffect(Unit) {
        agentRepository.fetchSettings(httpUrl) { map ->
            if (map != null) {
                map["business_name"]?.let { businessName = it }
                map["agent_name"]?.let { agentName = it }
                map["business_hours"]?.let { businessHours = it }
                map["agent_instructions"]?.let { agentInstructions = it }
                map["topics_to_avoid"]?.let { topicsToAvoid = it }
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
                            text = "Customize agent personality and details",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // Business Name Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Business Name",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = businessName,
                            onValueChange = { businessName = it },
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

                // AI Name Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "AI / Agent Name",
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

                // Business Hours Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Business Hours",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = businessHours,
                            onValueChange = { businessHours = it },
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

                // Agent Instructions Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Agent Instructions",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = agentInstructions,
                            onValueChange = { agentInstructions = it },
                            minLines = 3,
                            maxLines = 6,
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

                // Topics to Avoid Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Topics to Avoid",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = topicsToAvoid,
                            onValueChange = { topicsToAvoid = it },
                            minLines = 2,
                            maxLines = 4,
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
                        putString("business_name", businessName)
                        putString("agent_name", agentName)
                        putString("business_hours", businessHours)
                        putString("agent_instructions", agentInstructions)
                        putString("topics_to_avoid", topicsToAvoid)
                        putString("default_language", defaultLanguage)
                        apply()
                    }
                    
                    val settingsMap = mapOf(
                        "business_name" to businessName,
                        "agent_name" to agentName,
                        "business_hours" to businessHours,
                        "agent_instructions" to agentInstructions,
                        "topics_to_avoid" to topicsToAvoid,
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
