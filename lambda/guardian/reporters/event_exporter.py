"""Event export utility for generating CSV/PDF/JSON reports (memory optimized)"""

import csv
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any, Dict, List, Optional, Union

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

logger = logging.getLogger(__name__)


class EventExporter:
    """Export DynamoDB events to CSV, PDF, or JSON format (memory optimized)"""

    ALLOWED_FORMATS = ["csv", "pdf", "json"]
    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    @staticmethod
    def validate_format(format_str: str) -> bool:
        """Validate export format (Gemini recommended: strict whitelist)"""
        return format_str in EventExporter.ALLOWED_FORMATS

    @staticmethod
    def validate_severity(severity: Optional[str]) -> bool:
        """Validate severity filter"""
        if severity is None:
            return True
        return severity in EventExporter.SEVERITY_ORDER

    @classmethod
    def export_events(
        cls,
        events: List[Dict[str, Any]],
        format_str: str = "csv",
        summary: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Union[str, bytes]]:
        """
        Export events to specified format
        Returns: (file_path, file_content)
        """
        if not cls.validate_format(format_str):
            raise ValueError(f"Invalid format. Must be one of: {cls.ALLOWED_FORMATS}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # Use the platform temp dir (honours $TMPDIR; /tmp on Lambda) plus a
        # random suffix so report paths are not predictable and never collide
        # when two exports happen within the same second.
        tmp_dir = tempfile.gettempdir()
        unique = uuid.uuid4().hex[:8]

        if format_str == "csv":
            file_path = os.path.join(tmp_dir, f"report_{timestamp}_{unique}.csv")
            content = cls._export_to_csv(events)
        elif format_str == "pdf":
            file_path = os.path.join(tmp_dir, f"report_{timestamp}_{unique}.pdf")
            content = cls._export_to_pdf(events, summary)
        else:  # json
            file_path = os.path.join(tmp_dir, f"report_{timestamp}_{unique}.json")
            content = cls._export_to_json(events)

        return file_path, content

    @staticmethod
    def _export_to_csv(events: List[Dict[str, Any]]) -> str:
        """Export to CSV format (memory optimized with csv module, not pandas)"""
        output = StringIO()
        if not events:
            return output.getvalue()

        fieldnames = [
            "timestamp",
            "severity",
            "event_type",
            "resource_id",
            "message",
            "account_id",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for event in events:
            row = {
                "timestamp": event.get("timestamp", ""),
                "severity": event.get("severity", ""),
                "event_type": event.get("event_type", ""),
                "resource_id": event.get("resource_id", ""),
                "message": event.get("message", ""),
                "account_id": event.get("account_id", ""),
            }
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def _export_to_json(events: List[Dict[str, Any]]) -> str:
        """Export to JSON format (structured data for automation)"""
        return json.dumps(
            {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "event_count": len(events),
                "events": events,
            },
            indent=2,
            default=str,
        )

    @staticmethod
    def _export_to_pdf(
        events: List[Dict[str, Any]], summary: Optional[Dict[str, Any]] = None
    ) -> Union[str, bytes]:  # type: ignore
        """Export to PDF format with header, table, and summary (fpdf2)"""
        if FPDF is None:
            logger.warning("fpdf2 not installed, returning JSON instead")
            return EventExporter._export_to_json(events).encode()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)

        # Header
        pdf.cell(0, 10, "AWS Guardian Event Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, f"Generated: {datetime.now(timezone.utc).isoformat()}", ln=True)

        if summary:
            pdf.cell(0, 5, f"Total Events: {summary.get('total_events', 0)}", ln=True)
            pdf.ln(5)

        # Table
        pdf.set_font("Helvetica", "B", 9)
        col_widths = [30, 20, 25, 40, 35]
        headers = ["Timestamp", "Severity", "Type", "Resource", "Message"]

        for header, width in zip(headers, col_widths):
            pdf.cell(width, 7, header, border=1, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for event in events[:100]:  # Limit to 100 events per PDF (memory limit)
            cells = [
                event.get("timestamp", "")[:10],
                event.get("severity", "")[:10],
                event.get("event_type", "")[:15],
                event.get("resource_id", "")[:20],
                event.get("message", "")[:30],
            ]
            for cell, width in zip(cells, col_widths):
                pdf.cell(width, 6, str(cell), border=1)
            pdf.ln()

        # Summary
        if summary:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 5, "Summary by Severity", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for severity, count in summary.get("by_severity", {}).items():
                pdf.cell(0, 4, f"  {severity}: {count}", ln=True)

        return pdf.output()


def query_events_with_pagination(
    dynamodb_table,
    severity_filter: Optional[str] = None,
    days: int = 7,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Query DynamoDB with pagination support (Gemini recommended)
    Handles 1MB limit per DynamoDB response
    """
    events = []
    timestamp_cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query_params = {
        "KeyConditionExpression": "gsi_pk = :pk AND #ts > :ts",
        "ExpressionAttributeNames": {"#ts": "timestamp"},
        "ExpressionAttributeValues": {
            ":pk": "EVENT",
            ":ts": timestamp_cutoff,
        },
        "IndexName": "AllEventsIndex",
        "Limit": min(limit, 1000),
    }

    if severity_filter:
        query_params["FilterExpression"] = "severity = :sev"
        query_params["ExpressionAttributeValues"][":sev"] = severity_filter

    # Pagination loop (handles 1MB DynamoDB limit)
    while True:
        try:
            response = dynamodb_table.query(**query_params)
            events.extend(response.get("Items", []))

            if "LastEvaluatedKey" not in response or len(events) >= limit:
                break

            query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        except Exception as e:
            logger.error("DynamoDB query error: %s", e)
            break

    return events[:limit]
