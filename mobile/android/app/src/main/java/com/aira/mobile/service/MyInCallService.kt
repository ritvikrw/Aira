package com.aira.mobile.service

import android.telecom.Call
import android.telecom.CallAudioState
import android.telecom.InCallService
import android.util.Log

class MyInCallService : InCallService() {
    companion object {
        private const val TAG = "MyInCallService"
    }

    override fun onCallAdded(call: Call?) {
        super.onCallAdded(call)
        Log.i(TAG, "onCallAdded: call active, forcing speakerphone")
        try {
            @Suppress("DEPRECATION")
            setAudioRoute(CallAudioState.ROUTE_SPEAKER)
            Log.i(TAG, "setAudioRoute to SPEAKER successful")
        } catch (e: Exception) {
            Log.e(TAG, "Error setting call audio route to speaker", e)
        }
    }

    override fun onCallRemoved(call: Call?) {
        super.onCallRemoved(call)
        Log.i(TAG, "onCallRemoved")
    }
}
