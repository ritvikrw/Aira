package com.randomwalk.aira.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.randomwalk.aira.data.network.dto.TranscriptEntry
import com.randomwalk.aira.ui.components.formatDuration
import com.randomwalk.aira.ui.components.formatPhone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CallDetailScreen(
    onBack: () -> Unit,
    viewModel: CallDetailViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val call = uiState.call

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(call?.callerName ?: call?.callerPhone?.let { formatPhone(it) } ?: "Call") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            when {
                uiState.isLoading && call == null -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                uiState.error != null && call == null -> {
                    Text(
                        uiState.error ?: "Failed to load call",
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    )
                }
                call != null -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                    ) {
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Surface(
                                    color = MaterialTheme.colorScheme.surfaceVariant,
                                    shape = RoundedCornerShape(999.dp),
                                ) {
                                    Text(
                                        text = call.summary?.callCategory ?: "Other",
                                        style = MaterialTheme.typography.labelSmall,
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                                    )
                                }
                                Text(
                                    formatDuration(call.callDurationSeconds),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }

                        call.summary?.summaryText?.let { summary ->
                            item {
                                Text(
                                    "Summary",
                                    style = MaterialTheme.typography.labelLarge,
                                    modifier = Modifier.padding(top = 20.dp, bottom = 6.dp),
                                )
                                Text(summary, style = MaterialTheme.typography.bodyMedium)
                            }
                        }

                        val topics = call.summary?.keyTopics.orEmpty()
                        if (topics.isNotEmpty()) {
                            item {
                                Text(
                                    "Topics",
                                    style = MaterialTheme.typography.labelLarge,
                                    modifier = Modifier.padding(top = 20.dp, bottom = 6.dp),
                                )
                                Row {
                                    topics.forEach { topic ->
                                        Surface(
                                            color = MaterialTheme.colorScheme.secondaryContainer,
                                            shape = RoundedCornerShape(999.dp),
                                            modifier = Modifier.padding(end = 6.dp),
                                        ) {
                                            Text(
                                                topic,
                                                style = MaterialTheme.typography.labelSmall,
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        val actionItems = call.summary?.actionItems.orEmpty()
                        if (actionItems.isNotEmpty()) {
                            item {
                                Text(
                                    "Action items",
                                    style = MaterialTheme.typography.labelLarge,
                                    modifier = Modifier.padding(top = 20.dp, bottom = 6.dp),
                                )
                            }
                            items(actionItems) { action ->
                                Text("• $action", style = MaterialTheme.typography.bodyMedium)
                            }
                        }

                        item {
                            Text(
                                "Transcript",
                                style = MaterialTheme.typography.labelLarge,
                                modifier = Modifier.padding(top = 20.dp, bottom = 6.dp),
                            )
                        }
                        if (uiState.transcripts.isEmpty()) {
                            item {
                                Text(
                                    "No transcript available",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        } else {
                            items(uiState.transcripts, key = { it.id }) { entry ->
                                TranscriptBubble(entry)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TranscriptBubble(entry: TranscriptEntry) {
    val isAgent = entry.speaker == "agent"
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = if (isAgent) Arrangement.Start else Arrangement.End,
    ) {
        Surface(
            color = if (isAgent) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primaryContainer,
            shape = RoundedCornerShape(12.dp),
        ) {
            Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                Text(
                    if (isAgent) "Agent" else "Caller",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(entry.message, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
