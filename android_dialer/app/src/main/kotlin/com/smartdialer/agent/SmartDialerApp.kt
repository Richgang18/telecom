package com.smartdialer.agent

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class SmartDialerApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val mgr = getSystemService(NotificationManager::class.java)

            mgr.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_CALL,
                    "Active Call",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Shows during an active call"
                }
            )
        }
    }

    companion object {
        const val CHANNEL_CALL = "call_channel"
    }
}
