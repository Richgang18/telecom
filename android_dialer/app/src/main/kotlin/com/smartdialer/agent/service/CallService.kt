package com.smartdialer.agent.service

import android.app.*
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.smartdialer.agent.MainActivity
import com.smartdialer.agent.SmartDialerApp

/**
 * Foreground service that keeps the call alive when the app is backgrounded.
 * Started when a call connects, stopped when it ends.
 */
class CallService : Service() {

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val leadName  = intent?.getStringExtra("lead_name")  ?: "Unknown"
        val leadPhone = intent?.getStringExtra("lead_phone") ?: ""

        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val hangupIntent = PendingIntent.getService(
            this, 1,
            Intent(this, CallService::class.java).apply { action = ACTION_HANGUP },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(this, SmartDialerApp.CHANNEL_CALL)
            .setContentTitle("On call: $leadName")
            .setContentText(leadPhone)
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "End Call", hangupIntent)
            .build()

        startForeground(NOTIFICATION_ID, notification)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    companion object {
        const val ACTION_HANGUP   = "com.smartdialer.agent.ACTION_HANGUP"
        const val NOTIFICATION_ID = 1001

        fun start(context: android.content.Context, leadName: String, leadPhone: String) {
            val intent = Intent(context, CallService::class.java).apply {
                putExtra("lead_name",  leadName)
                putExtra("lead_phone", leadPhone)
            }
            context.startForegroundService(intent)
        }

        fun stop(context: android.content.Context) {
            context.stopService(Intent(context, CallService::class.java))
        }
    }
}
