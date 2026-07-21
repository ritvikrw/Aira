package com.aira.mobile.service

import android.app.role.RoleManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.telecom.PhoneAccount
import android.telecom.PhoneAccountHandle
import android.telecom.TelecomManager
import android.util.Log

class TelecomHelper(private val context: Context) {
    companion object {
        private const val TAG = "TelecomHelper"
        private const val ACCOUNT_ID = "AiraConnectionAccountId"
    }

    private val telecomManager = context.getSystemService(Context.TELECOM_SERVICE) as TelecomManager

    val phoneAccountHandle: PhoneAccountHandle = PhoneAccountHandle(
        ComponentName(context, MyConnectionService::class.java),
        ACCOUNT_ID
    )

    fun registerPhoneAccount() {
        try {
            val phoneAccount = PhoneAccount.builder(phoneAccountHandle, "Aira Call Agent")
                .setCapabilities(PhoneAccount.CAPABILITY_SELF_MANAGED)
                .setIcon(android.graphics.drawable.Icon.createWithResource(context, android.R.drawable.sym_def_app_icon))
                .build()
            telecomManager.registerPhoneAccount(phoneAccount)
            Log.i(TAG, "PhoneAccount registered successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Error registering PhoneAccount", e)
        }
    }

    fun isPhoneAccountRegistered(): Boolean {
        return try {
            val account = telecomManager.getPhoneAccount(phoneAccountHandle)
            account != null
        } catch (e: Exception) {
            false
        }
    }

    fun isDefaultDialer(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = context.getSystemService(Context.ROLE_SERVICE) as RoleManager
            roleManager.isRoleHeld(RoleManager.ROLE_DIALER)
        } else {
            val defaultDialerPackage = telecomManager.defaultDialerPackage
            defaultDialerPackage == context.packageName
        }
    }

    fun simulateIncomingCall(callerName: String = "Aira Test Incoming", callerNumber: String = "5550199") {
        try {
            // Ensure PhoneAccount is registered first
            registerPhoneAccount()
            
            val extras = Bundle().apply {
                putParcelable(TelecomManager.EXTRA_PHONE_ACCOUNT_HANDLE, phoneAccountHandle)
                val uri = Uri.fromParts("tel", callerNumber, null)
                putParcelable(TelecomManager.EXTRA_INCOMING_CALL_ADDRESS, uri)
                val incomingCallExtras = Bundle().apply {
                    putString(TelecomManager.EXTRA_CALL_BACK_NUMBER, callerNumber)
                    putString("caller_name", callerName)
                    putBoolean("is_simulation", true)
                }
                putBundle(TelecomManager.EXTRA_INCOMING_CALL_EXTRAS, incomingCallExtras)
            }
            
            telecomManager.addNewIncomingCall(phoneAccountHandle, extras)
            Log.i(TAG, "Simulated incoming call requested for: $callerName ($callerNumber)")
        } catch (e: Exception) {
            Log.e(TAG, "Error simulating incoming call", e)
        }
    }
}
