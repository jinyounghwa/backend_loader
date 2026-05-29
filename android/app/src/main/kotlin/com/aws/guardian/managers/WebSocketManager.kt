package com.aws.guardian.managers

import android.util.Log
import com.aws.guardian.models.Alert
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

class WebSocketManager {
    private val client = OkHttpClient()
    private var webSocket: WebSocket? = null
    private val listeners = mutableListOf<(Alert) -> Unit>()
    private var isConnected = false

    suspend fun connect(url: String, token: String): Result<Unit> = suspendCancellableCoroutine { continuation ->
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .build()

        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                isConnected = true
                Log.d("WebSocketManager", "WebSocket connected")
                continuation.resume(Result.success(Unit))
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                handleMessage(bytes.utf8())
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
                isConnected = false
                Log.e("WebSocketManager", "WebSocket failure: ${t.message}")
                continuation.resume(Result.failure(t))
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                isConnected = false
                Log.d("WebSocketManager", "WebSocket closed: $reason")
            }
        }

        webSocket = client.newWebSocket(request, listener)
    }

    fun disconnect() {
        webSocket?.close(1000, "Closing")
        isConnected = false
    }

    fun addListener(callback: (Alert) -> Unit) {
        listeners.add(callback)
    }

    fun removeListener(callback: (Alert) -> Unit) {
        listeners.remove(callback)
    }

    private fun handleMessage(jsonString: String) {
        try {
            // Parse JSON manually or use Gson
            val alert = parseAlertFromJson(jsonString)
            if (alert != null) {
                CoroutineScope(Dispatchers.Main).launch {
                    listeners.forEach { it(alert) }
                }
            }
        } catch (e: Exception) {
            Log.e("WebSocketManager", "Failed to parse message: ${e.message}")
        }
    }

    private fun parseAlertFromJson(json: String): Alert? {
        return try {
            // Simple JSON parsing (in production, use Gson or kotlinx.serialization)
            if (json.contains("\"id\"") && json.contains("\"severity\"")) {
                val idRegex = """"id"\s*:\s*"([^"]+)""".toRegex()
                val severityRegex = """"severity"\s*:\s*"([^"]+)""".toRegex()
                val titleRegex = """"title"\s*:\s*"([^"]+)""".toRegex()

                val id = idRegex.find(json)?.groupValues?.get(1) ?: return null
                val severity = severityRegex.find(json)?.groupValues?.get(1) ?: return null
                val title = titleRegex.find(json)?.groupValues?.get(1) ?: return null

                Alert(
                    id = id,
                    severity = severity,
                    title = title,
                    message = "Alert from WebSocket",
                    timestamp = System.currentTimeMillis(),
                    account = "unknown",
                    isRead = false
                )
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    fun isConnectedToWebSocket(): Boolean = isConnected
}
