package com.aira.mobile.presentation.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ChatScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF1A1B2F),
                        Color(0xFF161622)
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
            Text(
                text = "AIRA AI VOICE AGENT",
                color = Color(0xFF8A9AFA),
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 24.dp)
            )

            // Status Indicator / Waveform visualizer placeholder
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.weight(1f)
            ) {
                Surface(
                    modifier = Modifier.size(120.dp),
                    shape = RoundedCornerShape(60.dp),
                    color = Color(0xFF2C2D4A),
                    tonalElevation = 8.dp
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier.fillMaxSize()
                    ) {
                        // Simple active pulse representation
                        CircularProgressIndicator(
                            color = Color(0xFF5A6BFA),
                            strokeWidth = 4.dp,
                            modifier = Modifier.size(80.dp)
                        )
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "Awaiting Call...",
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Medium
                )
            }

            // Status details
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF23243C)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 24.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.Start
                ) {
                    Text(
                        text = "System Status",
                        color = Color(0xFF8A9AFA),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "WebSocket Server: Offline",
                        color = Color.Gray,
                        fontSize = 13.sp
                    )
                    Text(
                        text = "SIM Call Monitoring: Active",
                        color = Color(0xFF4CAF50),
                        fontSize = 13.sp
                    )
                }
            }
        }
    }
}
