package com.aira.mobile.service

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.telecom.TelecomManager
import android.telephony.TelephonyManager
import android.util.Log
import androidx.core.content.ContextCompat
import java.util.Calendar

class PhoneCallReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "PhoneCallReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        Log.i(TAG, "Phone State Changed: $state")

        if (state == TelephonyManager.EXTRA_STATE_RINGING) {
            val incomingNumber = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
            Log.i(TAG, "Incoming ringing call from: $incomingNumber")

            val prefs = context.getSharedPreferences("aira_prefs", Context.MODE_PRIVATE)
            val isEnabled = prefs.getBoolean("agent_enabled", false)

            if (!isEnabled) {
                Log.i(TAG, "AI Receptionist is disabled, ignoring call.")
                return
            }

            // 1. Blacklist Check
            if (incomingNumber != null) {
                val blacklistStr = prefs.getString("blacklist_numbers", "") ?: ""
                if (blacklistStr.isNotEmpty()) {
                    val blacklist = blacklistStr.split(",")
                        .map { it.trim().replace(Regex("[^0-9+]"), "") }
                        .filter { it.isNotEmpty() }
                    
                    val cleanIncoming = incomingNumber.replace(Regex("[^0-9+]"), "")
                    if (cleanIncoming.isNotEmpty() && blacklist.any { cleanIncoming.contains(it) || it.contains(cleanIncoming) }) {
                        Log.i(TAG, "Call from $incomingNumber matches blacklist filter. Ignoring call.")
                        return
                    }
                }
            }

            // 2. Do Not Disturb Check
            val dndEnabled = prefs.getBoolean("dnd_enabled", false)
            if (dndEnabled) {
                val startTimeStr = prefs.getString("dnd_start_time", "22:00") ?: "22:00"
                val endTimeStr = prefs.getString("dnd_end_time", "07:00") ?: "07:00"
                if (isDndActive(startTimeStr, endTimeStr)) {
                    Log.i(TAG, "DND active ($startTimeStr - $endTimeStr). Ignoring call.")
                    return
                }
            }

            Log.i(TAG, "AI Receptionist is enabled and call filters cleared, attempting to auto-answer call...")
            autoAnswerCall(context)
        }
    }

    private fun isDndActive(startTimeStr: String, endTimeStr: String): Boolean {
        try {
            val startParts = startTimeStr.split(":")
            val endParts = endTimeStr.split(":")
            if (startParts.size != 2 || endParts.size != 2) return false

            val startHour = startParts[0].toInt()
            val startMin = startParts[1].toInt()
            val endHour = endParts[0].toInt()
            val endMin = endParts[1].toInt()

            val calendar = Calendar.getInstance()
            val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
            val currentMin = calendar.get(Calendar.MINUTE)

            val nowMins = currentHour * 60 + currentMin
            val startMins = startHour * 60 + startMin
            val endMins = endHour * 60 + endMin

            return if (startMins <= endMins) {
                nowMins in startMins..endMins
            } else {
                // Overnight DND logic, e.g. 22:00 to 07:00
                nowMins >= startMins || nowMins <= endMins
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error checking DND status: startTime=$startTimeStr, endTime=$endTimeStr", e)
            return false
        }
    }

    private fun autoAnswerCall(context: Context) {
        val telecomManager = context.getSystemService(Context.TELECOM_SERVICE) as TelecomManager
        
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ANSWER_PHONE_CALLS) == PackageManager.PERMISSION_GRANTED) {
            try {
                // API 26+ method to answer call
                telecomManager.acceptRingingCall()
                Log.i(TAG, "acceptRingingCall invoked successfully!")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to auto-answer call using acceptRingingCall", e)
            }
        } else {
            Log.e(TAG, "ANSWER_PHONE_CALLS permission not granted, cannot auto-answer")
        }
    }
}
