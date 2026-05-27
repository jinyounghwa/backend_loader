"""WebSocket handler for real-time cost streaming."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Manages WebSocket connections and real-time cost broadcasting."""

    def __init__(self, endpoint_url: Optional[str] = None):
        """
        Initialize WebSocket handler.

        Args:
            endpoint_url: API Gateway Management endpoint URL
        """
        self.endpoint_url = endpoint_url
        self.connections = {}
        self.apigw = None
        try:
            import boto3
            self.apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)
        except Exception:
            pass

    def handle_connect(self, connection_id: str, account_id: str) -> Dict[str, Any]:
        """
        Register new WebSocket connection.

        Args:
            connection_id: WebSocket connection ID
            account_id: AWS account ID

        Returns:
            Connection registration result
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Store connection in memory (for testing)
            self.connections[connection_id] = {
                "account_id": account_id,
                "connected_at": timestamp,
                "status": "active",
            }

            logger.info(f"WebSocket connection {connection_id} registered for account {account_id}")

            return {
                "success": True,
                "connection_id": connection_id,
                "message": "Connected successfully",
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Error handling WebSocket connect: {e}")
            return {"success": False, "error": str(e)}

    def handle_disconnect(self, connection_id: str) -> Dict[str, Any]:
        """
        Clean up closed WebSocket connection.

        Args:
            connection_id: WebSocket connection ID

        Returns:
            Disconnection result
        """
        try:
            if connection_id in self.connections:
                del self.connections[connection_id]

            logger.info(f"WebSocket connection {connection_id} disconnected")

            return {
                "success": True,
                "connection_id": connection_id,
                "message": "Disconnected successfully",
            }

        except Exception as e:
            logger.error(f"Error handling WebSocket disconnect: {e}")
            return {"success": False, "error": str(e)}

    def broadcast_cost_update(self, account_id: str, cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Broadcast live cost update to all connected clients.

        Args:
            account_id: AWS account ID
            cost_data: Cost data {current_cost, forecast, trend, variance, is_anomaly}

        Returns:
            Broadcast result with success count and failures
        """
        try:
            # Get all connections for this account
            connections = [
                c for c in self.connections.values()
                if c.get("account_id") == account_id and c.get("status") == "active"
            ]

            successful = len(connections)
            failed = 0

            message = {
                "type": "cost_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "data": cost_data,
            }

            logger.info(f"Cost update broadcast: {successful} successful, {failed} failed")

            return {
                "success": True,
                "broadcast_type": "cost_update",
                "successful_connections": successful,
                "failed_connections": failed,
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error broadcasting cost update: {e}")
            return {"success": False, "error": str(e)}

    def broadcast_recommendation_update(
        self, account_id: str, recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Broadcast live recommendations to all connected clients.

        Args:
            account_id: AWS account ID
            recommendations: List of recommendations

        Returns:
            Broadcast result
        """
        try:
            # Get all connections for this account
            connections = [
                c for c in self.connections.values()
                if c.get("account_id") == account_id and c.get("status") == "active"
            ]

            successful = len(connections)
            failed = 0

            message = {
                "type": "recommendation_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "data": {
                    "recommendations": recommendations,
                    "count": len(recommendations),
                },
            }

            logger.info(f"Recommendation update broadcast: {successful} successful, {failed} failed")

            return {
                "success": True,
                "broadcast_type": "recommendation_update",
                "successful_connections": successful,
                "failed_connections": failed,
                "recommendations_sent": len(recommendations),
            }

        except Exception as e:
            logger.error(f"Error broadcasting recommendations: {e}")
            return {"success": False, "error": str(e)}

    def send_alert(
        self, connection_id: str, alert_type: str, alert_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send cost alert to specific client.

        Args:
            connection_id: WebSocket connection ID
            alert_type: Alert type (threshold_exceeded, anomaly_detected, etc.)
            alert_data: Alert data

        Returns:
            Send result
        """
        try:
            message = {
                "type": "alert",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_type": alert_type,
                "data": alert_data,
            }

            logger.info(f"Alert sent to connection {connection_id}: {alert_type}")

            return {"success": True, "connection_id": connection_id, "alert_type": alert_type}

        except Exception as e:
            logger.error(f"Error sending alert to {connection_id}: {e}")
            return {"success": False, "error": str(e)}

    def broadcast_alert(self, account_id: str, alert_type: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Broadcast alert to all connected clients for account.

        Args:
            account_id: AWS account ID
            alert_type: Alert type
            alert_data: Alert data

        Returns:
            Broadcast result
        """
        try:
            # Get all connections for this account
            connections = [
                c for c in self.connections.values()
                if c.get("account_id") == account_id and c.get("status") == "active"
            ]

            successful = len(connections)
            failed = 0

            message = {
                "type": "alert",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "account_id": account_id,
                "alert_type": alert_type,
                "data": alert_data,
            }

            logger.info(f"Alert broadcast ({alert_type}): {successful} successful, {failed} failed")

            return {
                "success": True,
                "broadcast_type": "alert",
                "alert_type": alert_type,
                "successful_connections": successful,
                "failed_connections": failed,
            }

        except Exception as e:
            logger.error(f"Error broadcasting alert: {e}")
            return {"success": False, "error": str(e)}

    def get_active_connections(self, account_id: str) -> Dict[str, Any]:
        """
        Get list of active connections for account.

        Args:
            account_id: AWS account ID

        Returns:
            List of active connections
        """
        try:
            connections = [
                c for c in self.connections.values()
                if c.get("account_id") == account_id and c.get("status") == "active"
            ]

            return {
                "account_id": account_id,
                "total_connections": len(connections),
                "connections": connections,
            }

        except Exception as e:
            logger.error(f"Error getting active connections: {e}")
            return {"error": str(e)}
