"""Shared API Gateway / Lambda proxy response builders.

Extracted from the identical ``success_response``/``error_response``
pairs previously copy-pasted across handler modules.
"""

import json
from typing import Any, Dict


def success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """Build a successful API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "body": json.dumps(data),
        "headers": {"Content-Type": "application/json"},
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Build an error API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": {"Content-Type": "application/json"},
    }
