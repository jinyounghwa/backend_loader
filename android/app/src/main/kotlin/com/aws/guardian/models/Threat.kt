package com.aws.guardian.models

import com.google.firebase.database.IgnoreExtraProperties
import java.io.Serializable

@IgnoreExtraProperties
data class Threat(
    val id: String = "",
    val severity: Int = 0,  // 0-100
    val title: String = "",
    val description: String = "",
    val timestamp: Long = 0L,
    val account: String = "",
    val service: String = "",
    val evidence: List<String> = emptyList()
) : Serializable

data class ThreatTimeline(
    val threats: List<Threat> = emptyList(),
    val total: Int = 0
)

data class ThreatStats(
    val criticalCount: Int = 0,
    val highCount: Int = 0,
    val mediumCount: Int = 0,
    val lowCount: Int = 0
)
