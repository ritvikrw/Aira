package com.randomwalk.aira.ui.components

import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException

fun formatDuration(seconds: Int?): String {
    if (seconds == null) return "--"
    if (seconds < 60) return "${seconds}s"
    val mins = seconds / 60
    val secs = seconds % 60
    return if (secs == 0) "${mins}m" else "${mins}m ${secs}s"
}

fun formatPhone(phone: String?): String {
    if (phone.isNullOrBlank()) return "Unknown"
    if (phone.startsWith("+91") && phone.length == 13) {
        val num = phone.substring(3)
        return "+91 ${num.substring(0, 5)} ${num.substring(5)}"
    }
    return phone
}

private val TIME_FORMATTER: DateTimeFormatter = DateTimeFormatter.ofPattern("h:mm a")

fun formatTime(isoTimestamp: String?): String {
    if (isoTimestamp.isNullOrBlank()) return ""
    return try {
        OffsetDateTime.parse(isoTimestamp).format(TIME_FORMATTER)
    } catch (e: DateTimeParseException) {
        ""
    }
}
