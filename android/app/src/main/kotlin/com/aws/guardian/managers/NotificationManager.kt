package com.aws.guardian.managers

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import com.aws.guardian.models.Alert
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.RemoteMessage

class NotificationManager(private val context: Context) {
    private val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    private val firebaseMessaging = FirebaseMessaging.getInstance()

    init {
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // Critical channel
            val criticalChannel = NotificationChannel(
                "critical",
                "Critical Alerts",
                NotificationManager.IMPORTANCE_MAX
            ).apply {
                description = "Critical security and cost alerts"
            }

            // High channel
            val highChannel = NotificationChannel(
                "high",
                "High Priority Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "High priority alerts"
            }

            // Medium channel
            val mediumChannel = NotificationChannel(
                "medium",
                "Medium Priority Alerts",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Medium priority alerts"
            }

            // Low channel
            val lowChannel = NotificationChannel(
                "low",
                "Low Priority Alerts",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Low priority alerts"
            }

            notificationManager.createNotificationChannels(
                listOf(criticalChannel, highChannel, mediumChannel, lowChannel)
            )
        }
    }

    fun sendLocalNotification(alert: Alert) {
        val channelId = when (alert.severity) {
            "CRITICAL" -> "critical"
            "HIGH" -> "high"
            "MEDIUM" -> "medium"
            else -> "low"
        }

        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(alert.title)
            .setContentText(alert.message)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        val notification = builder.build()
        notificationManager.notify(alert.id.hashCode(), notification)
    }

    fun handleRemoteMessage(message: RemoteMessage) {
        val data = message.data
        val title = data["title"] ?: "Guardian Alert"
        val body = data["body"] ?: "You have a new alert"
        val severity = data["severity"] ?: "LOW"

        val alert = Alert(
            id = data["id"] ?: System.currentTimeMillis().toString(),
            severity = severity,
            title = title,
            message = body,
            timestamp = System.currentTimeMillis(),
            account = data["account"] ?: "unknown",
            isRead = false
        )

        sendLocalNotification(alert)
    }

    fun subscribeToTopic(topic: String) {
        firebaseMessaging.subscribeToTopic(topic)
    }

    fun unsubscribeFromTopic(topic: String) {
        firebaseMessaging.unsubscribeFromTopic(topic)
    }

    fun requestPermission() {
        // FCM handles permission requests automatically on Android 13+
        firebaseMessaging.token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                // Send token to backend for registration
            }
        }
    }
}
