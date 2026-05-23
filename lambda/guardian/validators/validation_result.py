"""Validation Result for Sprint 34 Phase 2

Data class representing the result of rule validation.
Contains errors, warnings, and optional dry-run test results.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationResult:
    """Result of rule validation"""

    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        dry_run_threats: Optional[List[Dict[str, Any]]] = None,
        execution_time_ms: float = 0.0,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.dry_run_threats = dry_run_threats or []
        self.execution_time_ms = execution_time_ms
        self.validated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "dry_run_threats": self.dry_run_threats,
            "execution_time_ms": self.execution_time_ms,
            "validated_at": self.validated_at,
        }

    def add_error(self, error: str) -> None:
        """Add an error message"""
        if error not in self.errors:
            self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_dry_run_threat(self, threat: Dict[str, Any]) -> None:
        """Add a threat from dry-run evaluation"""
        self.dry_run_threats.append(threat)

    def __repr__(self) -> str:
        return f"ValidationResult(valid={self.is_valid}, errors={len(self.errors)}, warnings={len(self.warnings)}, threats={len(self.dry_run_threats)})"
