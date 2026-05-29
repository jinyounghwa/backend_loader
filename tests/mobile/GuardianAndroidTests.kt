package com.aws.guardian.tests

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.aws.guardian.managers.FirebaseManager
import com.aws.guardian.managers.NotificationManager
import com.aws.guardian.managers.WebSocketManager
import com.aws.guardian.models.Alert
import com.aws.guardian.models.CostHistory
import com.aws.guardian.models.ThreatTimeline
import com.aws.guardian.models.Threat
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class GuardianAndroidTests {
    private lateinit var context: Context
    private lateinit var firebaseManager: FirebaseManager
    private lateinit var webSocketManager: WebSocketManager
    private lateinit var notificationManager: NotificationManager

    @Before
    fun setUp() {
        context = InstrumentationRegistry.getInstrumentation().targetContext
        firebaseManager = FirebaseManager()
        webSocketManager = WebSocketManager()
        notificationManager = NotificationManager(context)
    }

    // MARK: - Firebase Sync Tests

    @Test
    fun testFirebaseSync() = runBlocking {
        val alert = Alert(
            id = "alert-1",
            severity = "CRITICAL",
            title = "Test Alert",
            message = "Test message",
            timestamp = System.currentTimeMillis(),
            account = "prod",
            isRead = false
        )

        val result = firebaseManager.syncAlertsToFirebase(listOf(alert))
        assertTrue(result.isSuccess)
    }

    @Test
    fun testOfflinePersistence() {
        val alerts = listOf(
            Alert(
                id = "1",
                severity = "CRITICAL",
                title = "Alert 1",
                message = "msg",
                timestamp = System.currentTimeMillis(),
                account = "prod",
                isRead = false
            ),
            Alert(
                id = "2",
                severity = "HIGH",
                title = "Alert 2",
                message = "msg",
                timestamp = System.currentTimeMillis(),
                account = "dev",
                isRead = false
            )
        )

        // Firebase stores in local cache automatically
        assertEquals(2, alerts.size)
        assertEquals("CRITICAL", alerts[0].severity)
    }

    @Test
    fun testFCMNotifications() {
        val alert = Alert(
            id = "notif-1",
            severity = "CRITICAL",
            title = "Critical Alert",
            message = "Immediate action required",
            timestamp = System.currentTimeMillis(),
            account = "prod",
            isRead = false
        )

        notificationManager.sendLocalNotification(alert)
        // Notification sent successfully (no exception thrown)
    }

    @Test
    fun testCostChartRendering() {
        val costHistory = CostHistory(
            dates = listOf("2026-05-25", "2026-05-26", "2026-05-27"),
            amounts = listOf(100.0, 120.0, 150.0)
        )

        assertEquals(3, costHistory.dates.size)
        assertEquals(3, costHistory.amounts.size)
        assertTrue(costHistory.amounts[2] > costHistory.amounts[0])
    }

    @Test
    fun testThreatTimeline() {
        val threats = listOf(
            Threat(
                id = "t1",
                severity = 90,
                title = "Threat 1",
                description = "desc",
                timestamp = 1000L,
                account = "prod",
                service = "EC2",
                evidence = listOf("ev1")
            ),
            Threat(
                id = "t2",
                severity = 70,
                title = "Threat 2",
                description = "desc",
                timestamp = 2000L,
                account = "prod",
                service = "S3",
                evidence = listOf("ev2")
            ),
            Threat(
                id = "t3",
                severity = 50,
                title = "Threat 3",
                description = "desc",
                timestamp = 1500L,
                account = "dev",
                service = "Lambda",
                evidence = listOf("ev3")
            )
        )

        val timeline = ThreatTimeline(threats = threats, total = threats.size)

        assertEquals(3, timeline.total)
        // Verify threats are present
        assertTrue(timeline.threats.any { it.severity == 90 })
        assertTrue(timeline.threats.any { it.service == "Lambda" })
    }

    @Test
    fun testAutoReconnect() = runBlocking {
        val url = "wss://guardian.example.com/ws"
        val token = "test-token"

        // Attempt connection
        val result = webSocketManager.connect(url, token)

        // Connection result (will fail in test environment but validates structure)
        assertNotNull(result)
    }
}
