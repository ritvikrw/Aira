package com.aira.mobile.presentation.fallback

import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FallbackSettingsScreen(
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val sharedPreferences = remember { context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE) }

    var fallbackEnabled by remember {
        mutableStateOf(sharedPreferences.getBoolean("fallback_enabled", true))
    }
    var blacklistNumbers by remember {
        mutableStateOf(sharedPreferences.getString("blacklist_numbers", "") ?: "")
    }
    var dndEnabled by remember {
        mutableStateOf(sharedPreferences.getBoolean("dnd_enabled", false))
    }
    var dndStartTime by remember {
        mutableStateOf(sharedPreferences.getString("dnd_start_time", "22:00") ?: "22:00")
    }
    var dndEndTime by remember {
        mutableStateOf(sharedPreferences.getString("dnd_end_time", "07:00") ?: "07:00")
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
                            text = "Safety & Fallbacks",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Manage agent blacklist and connection failover",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // WebSocket Fallback Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f).padding(end = 8.dp)) {
                            Text(
                                text = "Unreachable Server Fallback",
                                color = Color(0xFF8A9AFA),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "If the AI server is down, release call control to standard systems or disconnect.",
                                color = Color.Gray,
                                fontSize = 11.sp
                            )
                        }
                        Switch(
                            checked = fallbackEnabled,
                            onCheckedChange = { fallbackEnabled = it },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = Color(0xFF5A6BFA),
                                uncheckedThumbColor = Color.Gray,
                                uncheckedTrackColor = Color(0xFF12131C)
                            )
                        )
                    }
                }

                // Blacklist Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Blacklisted Phone Numbers",
                            color = Color(0xFF8A9AFA),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Calls matching these numbers won't be auto-answered",
                            color = Color.Gray,
                            fontSize = 11.sp
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        OutlinedTextField(
                            value = blacklistNumbers,
                            onValueChange = { blacklistNumbers = it },
                            placeholder = { Text("e.g. +919876543210, 5550199", color = Color.DarkGray) },
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

                // Do Not Disturb Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f).padding(end = 8.dp)) {
                                Text(
                                    text = "Do Not Disturb (DND) Hours",
                                    color = Color(0xFF8A9AFA),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "Turn off auto-answering during specific times",
                                    color = Color.Gray,
                                    fontSize = 11.sp
                                )
                            }
                            Switch(
                                checked = dndEnabled,
                                onCheckedChange = { dndEnabled = it },
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = Color.White,
                                    checkedTrackColor = Color(0xFF5A6BFA),
                                    uncheckedThumbColor = Color.Gray,
                                    uncheckedTrackColor = Color(0xFF12131C)
                                )
                            )
                        }

                        if (dndEnabled) {
                            Spacer(modifier = Modifier.height(16.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "Start Time (24h format)",
                                        color = Color.LightGray,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Spacer(modifier = Modifier.height(6.dp))
                                    OutlinedTextField(
                                        value = dndStartTime,
                                        onValueChange = { dndStartTime = it },
                                        placeholder = { Text("22:00", color = Color.DarkGray) },
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
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "End Time (24h format)",
                                        color = Color.LightGray,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Spacer(modifier = Modifier.height(6.dp))
                                    OutlinedTextField(
                                        value = dndEndTime,
                                        onValueChange = { dndEndTime = it },
                                        placeholder = { Text("07:00", color = Color.DarkGray) },
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
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Save Button
            Button(
                onClick = {
                    // Quick validation on DND times if enabled
                    if (dndEnabled) {
                        val startParts = dndStartTime.split(":")
                        val endParts = dndEndTime.split(":")
                        if (startParts.size != 2 || endParts.size != 2 || 
                            startParts[0].toIntOrNull() == null || startParts[1].toIntOrNull() == null ||
                            endParts[0].toIntOrNull() == null || endParts[1].toIntOrNull() == null) {
                            Toast.makeText(context, "Please enter valid DND hours (HH:MM)", Toast.LENGTH_LONG).show()
                            return@Button
                        }
                    }

                    sharedPreferences.edit().apply {
                        putBoolean("fallback_enabled", fallbackEnabled)
                        putString("blacklist_numbers", blacklistNumbers)
                        putBoolean("dnd_enabled", dndEnabled)
                        putString("dnd_start_time", dndStartTime)
                        putString("dnd_end_time", dndEndTime)
                        apply()
                    }
                    Toast.makeText(context, "Safety settings saved successfully!", Toast.LENGTH_SHORT).show()
                    onNavigateBack()
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA)),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Text(
                    text = "Save Safety Settings",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
