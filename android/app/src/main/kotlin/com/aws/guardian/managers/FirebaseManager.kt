package com.aws.guardian.managers

import android.util.Log
import com.aws.guardian.models.Alert
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

class FirebaseManager {
    private val database = FirebaseDatabase.getInstance()
    private val alertsRef = database.getReference("alerts")

    init {
        // Enable offline persistence
        database.setPersistenceEnabled(true)
    }

    suspend fun syncAlertsToFirebase(alerts: List<Alert>): Result<Unit> = suspendCancellableCoroutine { continuation ->
        alertsRef.setValue(alerts).addOnCompleteListener { task ->
            if (task.isSuccessful) {
                Log.d("FirebaseManager", "Alerts synced successfully")
                continuation.resume(Result.success(Unit))
            } else {
                Log.e("FirebaseManager", "Sync failed: ${task.exception?.message}")
                continuation.resume(Result.failure(task.exception ?: Exception("Unknown error")))
            }
        }
    }

    fun fetchAlertsFromFirebase(callback: (List<Alert>) -> Unit) {
        alertsRef.addValueEventListener(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                val alerts = mutableListOf<Alert>()
                for (child in snapshot.children) {
                    val alert = child.getValue(Alert::class.java)
                    if (alert != null) {
                        alerts.add(alert)
                    }
                }
                // Sort by timestamp descending
                alerts.sortByDescending { it.timestamp }
                callback(alerts)
            }

            override fun onCancelled(error: DatabaseError) {
                Log.e("FirebaseManager", "Database error: ${error.message}")
                callback(emptyList())
            }
        })
    }

    suspend fun deleteAlert(alertId: String): Result<Unit> = suspendCancellableCoroutine { continuation ->
        alertsRef.child(alertId).removeValue().addOnCompleteListener { task ->
            if (task.isSuccessful) {
                continuation.resume(Result.success(Unit))
            } else {
                continuation.resume(Result.failure(task.exception ?: Exception("Failed to delete")))
            }
        }
    }

    fun listenForAlertUpdates(callback: (Alert) -> Unit) {
        alertsRef.addChildEventListener(object : com.google.firebase.database.ChildEventListener {
            override fun onChildAdded(snapshot: DataSnapshot, previousChildName: String?) {
                snapshot.getValue(Alert::class.java)?.let(callback)
            }

            override fun onChildChanged(snapshot: DataSnapshot, previousChildName: String?) {
                snapshot.getValue(Alert::class.java)?.let(callback)
            }

            override fun onChildRemoved(snapshot: DataSnapshot) {}
            override fun onChildMoved(snapshot: DataSnapshot, previousChildName: String?) {}
            override fun onCancelled(error: DatabaseError) {
                Log.e("FirebaseManager", "Listener cancelled: ${error.message}")
            }
        })
    }
}
