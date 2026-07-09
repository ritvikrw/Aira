package com.aira.mobile.presentation.status

import android.content.Context
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aira.mobile.domain.repository.AgentRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

enum class TestState {
    IDLE,
    CONNECTING,
    PINGING,
    SUCCESS,
    FAILED
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConnectionStatusScreen(
    agentRepository: AgentRepository,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val sharedPreferences = remember { context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE) }
    val scope = rememberCoroutineScope()

    var serverUrl by remember {
        mutableStateOf(sharedPreferences.getString("server_url", "wss://web-ninaiv-production-c6ae.up.railway.app/ws") ?: "wss://web-ninaiv-production-c6ae.up.railway.app/ws")
    }

    var testState by remember { mutableStateOf(TestState.IDLE) }
    var latencyMs by remember { mutableStateOf<Long?>(null) }
    var errorMessage by remember { mutableStateOf("") }

    val statusColor = when (testState) {
        TestState.IDLE -> Color.Gray
        TestState.CONNECTING, TestState.PINGING -> Color(0xFFFFC107)
        TestState.SUCCESS -> Color(0xFF4CAF50)
        TestState.FAILED -> Color(0xFFE91E63)
    }

    val statusText = when (testState) {
        TestState.IDLE -> "Ready to test"
        TestState.CONNECTING -> "Connecting to socket..."
        TestState.PINGING -> "Sending heartbeat..."
        TestState.SUCCESS -> "Connected successfully!"
        TestState.FAILED -> "Connection failed"
    }

    // Pulse animation for testing state
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseAlpha"
    )

    fun runConnectionTest() {
        scope.launch {
            // Save URL
            sharedPreferences.edit().putString("server_url", serverUrl).apply()
            
            testState = TestState.CONNECTING
            latencyMs = null
            errorMessage = ""

            var startTime = 0L

            val listener = object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    startTime = System.currentTimeMillis()
                    testState = TestState.PINGING
                    // Send a small heartbeat ping
                    agentRepository.sendText("ping")
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    if (text.contains("pong") || text == "pong") {
                        val endTime = System.currentTimeMillis()
                        latencyMs = endTime - startTime
                        testState = TestState.SUCCESS
                    }
                    agentRepository.disconnect()
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    errorMessage = t.message ?: "Unknown websocket socket failure"
                    testState = TestState.FAILED
                    agentRepository.disconnect()
                }

                override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                    webSocket.close(1000, null)
                }
            }

            try {
                agentRepository.connect(serverUrl, listener)
                
                // Timeout watcher (5 seconds)
                delay(5000)
                if (testState == TestState.CONNECTING || testState == TestState.PINGING) {
                    errorMessage = "Connection timed out after 5s"
                    testState = TestState.FAILED
                    agentRepository.disconnect()
                }
            } catch (e: Exception) {
                errorMessage = e.message ?: "Failed to initialize WebSocket client"
                testState = TestState.FAILED
                agentRepository.disconnect()
            }
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
                            text = "Connection Status",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Test WebSocket server transport connection",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // URL Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Server WebSocket URL",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = serverUrl,
                            onValueChange = { serverUrl = it },
                            placeholder = { Text("ws://10.0.2.2:8000/ws", color = Color.DarkGray) },
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

                // Status Visualization Card
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "Network Status Monitor",
                            color = Color(0xFF8A9AFA),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.align(Alignment.Start)
                        )
                        Spacer(modifier = Modifier.height(24.dp))

                        // Status Light Ring
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier.size(100.dp)
                        ) {
                            val alpha = if (testState == TestState.CONNECTING || testState == TestState.PINGING) pulseAlpha else 0.2f
                            Box(
                                modifier = Modifier
                                    .size(80.dp)
                                    .clip(CircleShape)
                                    .background(statusColor.copy(alpha = alpha))
                            )
                            Box(
                                modifier = Modifier
                                    .size(48.dp)
                                    .clip(CircleShape)
                                    .background(statusColor)
                            )
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        Text(
                            text = statusText,
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )

                        latencyMs?.let {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = "Round-Trip Latency: $it ms",
                                color = Color(0xFF4CAF50),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        if (errorMessage.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(Color(0xFFE91E63).copy(alpha = 0.15f), RoundedCornerShape(8.dp))
                                    .padding(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Info,
                                    contentDescription = null,
                                    tint = Color(0xFFE91E63),
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = errorMessage,
                                    color = Color(0xFFE91E63),
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Test Button
            Button(
                onClick = { runConnectionTest() },
                enabled = testState != TestState.CONNECTING && testState != TestState.PINGING,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A6BFA)),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Text(
                    text = "Test Connection",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
