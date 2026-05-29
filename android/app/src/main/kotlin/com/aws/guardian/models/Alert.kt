package com.aws.guardian.models

import com.google.firebase.database.IgnoreExtraProperties
import java.io.Serializable

@IgnoreExtraProperties
data class Alert(
    val id: String = "",
    val severity: String = "",  // CRITICAL, HIGH, MEDIUM, LOW
    val title: String = "",
    val message: String = "",
    val timestamp: Long = 0L,
    val account: String = "",
    val isRead: Boolean = false
) : Serializable {
    enum class Severity(val value: String) {
        CRITICAL("CRITICAL"),
        HIGH("HIGH"),
        MEDIUM("MEDIUM"),
        LOW("LOW")
    }
}

data class AlertListResponse(
    val alerts: List<Alert> = emptyList(),
    val total: Int = 0
)
