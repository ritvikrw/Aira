package com.aira.mobile.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.telecom.Connection
import android.telecom.ConnectionRequest
import android.telecom.ConnectionService
import android.telecom.PhoneAccountHandle
import android.telecom.TelecomManager
import android.util.Log
import androidx.core.app.NotificationCompat

class MyConnectionService : ConnectionService() {
    companion object {
        private const val TAG = "MyConnectionService"
        private const val CHANNEL_ID = "aira_connection_channel"
        private const val NOTIFICATION_ID = 9999
        
        private var activeService: MyConnectionService? = null
        
        fun startForeground(notificationText: String) {
            activeService?.startForegroundInternal(notificationText)
        }
        
        fun stopForeground() {
            activeService?.stopForegroundInternal()
        }
    }

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        activeService = this
        createNotificationChannel()
        Log.i(TAG, "Service onCreate called")
    }

    override fun onDestroy() {
        activeService = null
        releaseWakeLock()
        super.onDestroy()
        Log.i(TAG, "Service onDestroy called")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Aira Connection Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps Aira active during background calls"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun startForegroundInternal(text: String) {
        acquireWakeLock()
        
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Aira Voice Receptionist")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.sym_action_call)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            var serviceType = ServiceInfo.FOREGROUND_SERVICE_TYPE_PHONE_CALL
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                serviceType = serviceType or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            }
            startForeground(NOTIFICATION_ID, notification, serviceType)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
        Log.i(TAG, "Service started foreground with text: $text")
    }

    private fun stopForegroundInternal() {
        releaseWakeLock()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            stopForeground(true)
        }
        Log.i(TAG, "Service stopped foreground")
    }

    private fun acquireWakeLock() {
        if (wakeLock == null) {
            val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Aira:CallWakeLock").apply {
                acquire()
            }
            Log.i(TAG, "WakeLock acquired")
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
            }
            wakeLock = null
            Log.i(TAG, "WakeLock released")
        }
    }

    override fun onCreateIncomingConnection(
        connectionManagerPhoneAccount: PhoneAccountHandle?,
        request: ConnectionRequest?
    ): Connection {
        Log.i(TAG, "onCreateIncomingConnection: Incoming call received, creating connection")
        val connection = MyConnection(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            connection.setAddress(request?.address, TelecomManager.PRESENTATION_ALLOWED)
        }
        connection.initializingCall()
        return connection
    }

    override fun onCreateOutgoingConnection(
        connectionManagerPhoneAccount: PhoneAccountHandle?,
        request: ConnectionRequest?
    ): Connection {
        Log.i(TAG, "onCreateOutgoingConnection: Creating outgoing connection")
        val connection = MyConnection(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            connection.setAddress(request?.address, TelecomManager.PRESENTATION_ALLOWED)
        }
        connection.initializingCall()
        return connection
    }

    override fun onCreateIncomingConnectionFailed(
        connectionManagerPhoneAccount: PhoneAccountHandle?,
        request: ConnectionRequest?
    ) {
        Log.e(TAG, "onCreateIncomingConnectionFailed")
    }

    override fun onCreateOutgoingConnectionFailed(
        connectionManagerPhoneAccount: PhoneAccountHandle?,
        request: ConnectionRequest?
    ) {
        Log.e(TAG, "onCreateOutgoingConnectionFailed")
    }
}
