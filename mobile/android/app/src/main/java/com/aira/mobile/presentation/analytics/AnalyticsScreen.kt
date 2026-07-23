package com.aira.mobile.presentation.analytics

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aira.mobile.domain.repository.AgentRepository
import org.json.JSONObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyticsScreen(
    agentRepository: AgentRepository,
    onNavigateBack: () -> Unit
) {
    val httpUrl = "https://web-ninaiv-production-c6ae.up.railway.app"
    var isLoading by remember { mutableStateOf(true) }
    var totalCalls by remember { mutableStateOf(0) }
    var todayCalls by remember { mutableStateOf(0) }
    var avgDuration by remember { mutableStateOf(0.0) }
    var busiestHour by remember { mutableStateOf("N/A") }
    var activeCalls by remember { mutableStateOf(0) }
    
    // Call Volume data: List of Pair(Day label, Call count)
    var volumeOverTime by remember { mutableStateOf<List<Pair<String, Int>>>(emptyList()) }
    
    // Categories: Category Name -> Call count
    var categoriesMap by remember { mutableStateOf<Map<String, Int>>(emptyMap()) }
    
    // Top Topics: List of Pair(Topic Name, Count)
    var topTopicsList by remember { mutableStateOf<List<Pair<String, Int>>>(emptyList()) }

    fun refreshAnalytics() {
        isLoading = true
        agentRepository.fetchAnalytics(httpUrl) { json ->
            isLoading = false
            if (json != null) {
                try {
                    totalCalls = json.optInt("total_calls", 0)
                    todayCalls = json.optInt("today_calls", 0)
                    avgDuration = json.optDouble("avg_duration", 0.0)
                    busiestHour = json.optString("busiest_hour", "N/A")
                    activeCalls = json.optInt("active_calls", 0)

                    val volumeArray = json.optJSONArray("volume_over_time")
                    val volList = mutableListOf<Pair<String, Int>>()
                    if (volumeArray != null) {
                        for (i in 0 until volumeArray.length()) {
                            val item = volumeArray.optJSONObject(i)
                            if (item != null) {
                                val label = item.optString("label", "")
                                val value = item.optInt("value", 0)
                                if (label.isNotEmpty()) {
                                    volList.add(label to value)
                                }
                            }
                        }
                    }
                    volumeOverTime = volList

                    val categoriesJson = json.optJSONObject("calls_by_category") ?: JSONObject()
                    val catMap = mutableMapOf<String, Int>()
                    val catKeys = categoriesJson.keys()
                    while (catKeys.hasNext()) {
                        val key = catKeys.next()
                        catMap[key] = categoriesJson.optInt(key, 0)
                    }
                    categoriesMap = catMap

                    val topicsArray = json.optJSONArray("top_topics")
                    val topics = mutableListOf<Pair<String, Int>>()
                    if (topicsArray != null) {
                        for (i in 0 until topicsArray.length()) {
                            val item = topicsArray.optJSONObject(i)
                            if (item != null) {
                                val topic = item.optString("topic", "")
                                val count = item.optInt("count", 0)
                                if (topic.isNotEmpty()) {
                                    topics.add(topic to count)
                                }
                            }
                        }
                    }
                    topTopicsList = topics
                } catch (e: Exception) {
                    android.util.Log.e("AnalyticsScreen", "Error parsing analytics", e)
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshAnalytics()
    }

    val formattedDuration = remember(avgDuration) {
        if (avgDuration <= 0) "0s" else {
            val mins = (avgDuration / 60).toInt()
            val secs = (avgDuration % 60).toInt()
            if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
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
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
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
                            text = "Analytics",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Database statistics and metrics",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                IconButton(
                    onClick = { refreshAnalytics() },
                    colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF2C2D4A))
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh",
                        tint = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            if (isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize().weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color(0xFF5A6BFA))
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Metric Summary Cards
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        MetricCard(
                            title = "Calls — All Time",
                            value = "$totalCalls",
                            subtext = "$todayCalls today",
                            modifier = Modifier.weight(1f)
                        )
                        MetricCard(
                            title = "Avg Duration",
                            value = formattedDuration,
                            subtext = "per call",
                            modifier = Modifier.weight(1f)
                        )
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        MetricCard(
                            title = "Busiest Hour",
                            value = busiestHour,
                            subtext = "Calcutta",
                            modifier = Modifier.weight(1f)
                        )
                        MetricCard(
                            title = "Active Calls",
                            value = "$activeCalls",
                            subtext = "Live count",
                            modifier = Modifier.weight(1f)
                        )
                    }

                    // Call Volume Chart Card
                    CallVolumeChart(volumeData = volumeOverTime)

                    // Calls by Category
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = "CALLS BY CATEGORY",
                                color = Color(0xFF8A9AFA),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(12.dp))

                            val sortedCategories = categoriesMap.toList().sortedByDescending { it.second }
                            if (sortedCategories.isEmpty()) {
                                Text(
                                    text = "No category data available",
                                    color = Color.Gray,
                                    fontSize = 13.sp
                                )
                            } else {
                                sortedCategories.forEach { (catName, catCount) ->
                                    CategoryProgressRow(
                                        category = catName,
                                        count = catCount,
                                        total = totalCalls
                                    )
                                    Spacer(modifier = Modifier.height(12.dp))
                                }
                            }
                        }
                    }

                    // Top Topics
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
                        modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = "TOP TOPICS",
                                color = Color(0xFF8A9AFA),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(12.dp))

                            if (topTopicsList.isEmpty()) {
                                Text(
                                    text = "No topic data available",
                                    color = Color.Gray,
                                    fontSize = 13.sp
                                )
                            } else {
                                // Horizontally scrollable row of chip tags — optimized for phone layouts
                                Row(
                                    modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    topTopicsList.forEach { topic ->
                                        SuggestionChip(
                                            onClick = {},
                                            label = { 
                                                Text(
                                                    text = "${topic.first} (${topic.second})", 
                                                    color = Color(0xFFDCDCDC),
                                                    fontSize = 12.sp
                                                ) 
                                            },
                                            colors = SuggestionChipDefaults.suggestionChipColors(
                                                containerColor = Color(0xFF2C2D4A)
                                            ),
                                            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF5A6BFA).copy(alpha = 0.4f))
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MetricCard(
    title: String,
    value: String,
    subtext: String,
    modifier: Modifier = Modifier
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                color = Color.Gray,
                fontSize = 11.sp,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = value,
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.ExtraBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = subtext,
                color = Color.Gray,
                fontSize = 11.sp
            )
        }
    }
}

@Composable
fun CategoryProgressRow(
    category: String,
    count: Int,
    total: Int
) {
    val percentage = if (total > 0) count.toFloat() / total else 0f
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = category, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Medium)
            Text(text = "$count (${(percentage * 100).toInt()}%)", color = Color.Gray, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = percentage,
            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
            color = Color(0xFF5A6BFA),
            trackColor = Color(0xFF12131C)
        )
    }
}

@Composable
fun CallVolumeChart(volumeData: List<Pair<String, Int>>) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1F35)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "CALL VOLUME — DAILY",
                color = Color(0xFF8A9AFA),
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(16.dp))

            if (volumeData.isEmpty()) {
                Text(
                    text = "No call volume data available",
                    color = Color.Gray,
                    fontSize = 13.sp
                )
            } else {
                val maxVal = remember(volumeData) { volumeData.maxOfOrNull { it.second } ?: 1 }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(150.dp)
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalAlignment = Alignment.Bottom
                ) {
                    volumeData.forEach { data ->
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Bottom,
                            modifier = Modifier.fillMaxHeight().width(48.dp)
                        ) {
                            Text(
                                text = "${data.second}",
                                color = Color.White,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Box(
                                modifier = Modifier
                                    .width(24.dp)
                                    .fillMaxHeight((data.second.toFloat() / maxVal).coerceIn(0.08f, 1f))
                                    .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                                    .background(
                                        brush = Brush.verticalGradient(
                                            colors = listOf(
                                                Color(0xFF8A9AFA),
                                                Color(0xFF5A6BFA)
                                            )
                                        )
                                    )
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = data.first,
                                color = Color.Gray,
                                fontSize = 10.sp,
                                maxLines = 1
                            )
                        }
                    }
                }
            }
        }
    }
}
