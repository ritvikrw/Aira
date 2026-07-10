package com.randomwalk.aira.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.randomwalk.aira.data.network.dto.CallListItem
import com.randomwalk.aira.ui.components.formatDuration
import com.randomwalk.aira.ui.components.formatPhone
import com.randomwalk.aira.ui.components.formatTime

private val CATEGORY_COLORS: Map<String, Color> = mapOf(
    "Product Enquiry" to Color(0xFFEFF6FF),
    "Support Request" to Color(0xFFF5F3FF),
    "Billing & Pricing" to Color(0xFFF0FDF4),
    "Appointment / Booking" to Color(0xFFF0FDFA),
    "Complaint" to Color(0xFFFEF2F2),
)

@Composable
fun CallCard(call: CallListItem, onClick: () -> Unit) {
    val category = call.callCategory ?: "Other"
    val categoryColor = CATEGORY_COLORS[category] ?: MaterialTheme.colorScheme.surfaceVariant
    val phoneDisplay = call.callerPhone?.takeIf { it != "+00 00000 00000" } ?: call.callerId

    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = call.callerName
                        ?: phoneDisplay?.let { formatPhone(it) }
                        ?: "Unknown caller",
                    fontWeight = FontWeight.SemiBold,
                    fontStyle = if (call.callerName == null && phoneDisplay == null) FontStyle.Italic else FontStyle.Normal,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = formatTime(call.callStartTime),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    color = categoryColor,
                    shape = RoundedCornerShape(999.dp),
                ) {
                    Text(
                        text = category,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                    )
                }
                Text(
                    text = formatDuration(call.callDurationSeconds),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            call.summaryText?.let { summary ->
                Text(
                    text = summary,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }

            if (call.status == "active") {
                Surface(
                    color = Color(0xFFFEF2F2),
                    shape = RoundedCornerShape(999.dp),
                    modifier = Modifier.padding(top = 6.dp),
                ) {
                    Text(
                        text = "● Live",
                        color = Color(0xFFDC2626),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                    )
                }
            }
        }
    }
}
