package com.aws.guardian.models

import com.google.firebase.database.IgnoreExtraProperties
import java.io.Serializable

@IgnoreExtraProperties
data class Cost(
    val id: String = "",
    val date: Long = 0L,
    val amount: Double = 0.0,
    val service: String = "",
    val account: String = ""
) : Serializable

data class CostSummary(
    val dailyCost: Double = 0.0,
    val monthlyCost: Double = 0.0,
    val trend: Double = 0.0,  // percentage change
    val byService: Map<String, Double> = emptyMap(),
    val byAccount: Map<String, Double> = emptyMap()
)

data class CostHistory(
    val dates: List<String> = emptyList(),
    val amounts: List<Double> = emptyList()
)
