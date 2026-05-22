"""IAM Policy analyzer for AWS Guardian."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.exceptions import ClientError

from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class IAMPolicyAnalyzer(BaseChecker):
    """Analyze IAM policies for overly-permissive actions."""

    RISKY_ACTIONS = {
        "*": "CRITICAL",  # All actions
        "iam:*": "HIGH",  # All IAM actions
        "ec2:*": "HIGH",  # All EC2 actions
        "s3:*": "HIGH",  # All S3 actions
        "dynamodb:*": "HIGH",  # All DynamoDB actions
    }

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients or {}, config or {}, account_id, credentials)
        self.iam_client = self.clients.get("iam")
        if self.iam_client is None:
            self.iam_client = boto3.client("iam", **Config.get_boto3_kwargs())

    def check(self) -> CheckResult:
        """Analyze IAM policies for risky patterns."""
        self._log_check_start("IAMPolicyAnalyzer")
        try:
            policies = self._get_all_policies()
            return self._analyze_policies(policies)
        except ClientError as e:
            return self._handle_client_error("IAMPolicyAnalyzer", e)
        except Exception as e:
            return self._handle_generic_error("IAMPolicyAnalyzer", e)

    def _get_all_policies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all inline policies from users and roles."""
        policies: Dict[str, List[Dict[str, Any]]] = {
            "users": [],
            "roles": [],
        }

        try:
            # Get user policies
            paginator = self.iam_client.get_paginator("list_users")
            for page in paginator.paginate():
                for user in page.get("Users", []):
                    user_name = user["UserName"]
                    user_policies = self._get_user_inline_policies(user_name)
                    for policy_doc in user_policies:
                        policies["users"].append(
                            {
                                "entity": user_name,
                                "type": "user",
                                "policy": policy_doc,
                            }
                        )
        except ClientError as e:
            logger.error("Error fetching users: %s", e)
        except Exception as e:
            logger.error("Error fetching user policies: %s", e)

        try:
            # Get role policies
            paginator = self.iam_client.get_paginator("list_roles")
            for page in paginator.paginate():
                for role in page.get("Roles", []):
                    role_name = role["RoleName"]
                    role_policies = self._get_role_inline_policies(role_name)
                    for policy_doc in role_policies:
                        policies["roles"].append(
                            {
                                "entity": role_name,
                                "type": "role",
                                "policy": policy_doc,
                            }
                        )
        except ClientError as e:
            logger.error("Error fetching roles: %s", e)
        except Exception as e:
            logger.error("Error fetching role policies: %s", e)

        return policies

    def _get_user_inline_policies(self, user_name: str) -> List[Dict[str, Any]]:
        """Get inline policies for a user."""
        policies = []
        try:
            paginator = self.iam_client.get_paginator("list_user_policies")
            for page in paginator.paginate(UserName=user_name):
                for policy_name in page.get("PolicyNames", []):
                    try:
                        response = self.iam_client.get_user_policy(
                            UserName=user_name, PolicyName=policy_name
                        )
                        policy_doc = response.get("PolicyDocument", {})
                        if isinstance(policy_doc, str):
                            policy_doc = json.loads(policy_doc)
                        policies.append(policy_doc)
                    except (ClientError, json.JSONDecodeError) as e:
                        logger.debug("Error fetching user policy %s: %s", policy_name, e)
        except ClientError as e:
            logger.debug("Error listing user policies: %s", e)
        return policies

    def _get_role_inline_policies(self, role_name: str) -> List[Dict[str, Any]]:
        """Get inline policies for a role."""
        policies = []
        try:
            paginator = self.iam_client.get_paginator("list_role_policies")
            for page in paginator.paginate(RoleName=role_name):
                for policy_name in page.get("PolicyNames", []):
                    try:
                        response = self.iam_client.get_role_policy(
                            RoleName=role_name, PolicyName=policy_name
                        )
                        policy_doc = response.get("PolicyDocument", {})
                        if isinstance(policy_doc, str):
                            policy_doc = json.loads(policy_doc)
                        policies.append(policy_doc)
                    except (ClientError, json.JSONDecodeError) as e:
                        logger.debug("Error fetching role policy %s: %s", policy_name, e)
        except ClientError as e:
            logger.debug("Error listing role policies: %s", e)
        return policies

    def _analyze_policies(self, policies: Dict[str, List[Dict[str, Any]]]) -> CheckResult:
        """Analyze policies for risky patterns."""
        findings: List[Dict[str, Any]] = []
        severity_map: Set[str] = set()

        for entity_type, entity_list in policies.items():
            for entity_policy in entity_list:
                entity = entity_policy["entity"]
                policy_doc = entity_policy["policy"]

                policy_findings = self._analyze_policy_document(policy_doc, entity, entity_type)
                for finding in policy_findings:
                    findings.append(finding)
                    severity_map.add(finding["severity"])

        details: Dict[str, Any] = {
            "is_anomaly": len(findings) > 0,
            "total_policies_scanned": len(policies["users"]) + len(policies["roles"]),
            "risky_policies": len(findings),
            "findings": findings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not findings:
            return CheckResult(
                severity="INFO",
                title="IAM Policy Analysis",
                message="No overly-permissive policies detected",
                details=details,
            )

        # Determine overall severity
        overall_severity = "LOW"
        if "CRITICAL" in severity_map:
            overall_severity = "CRITICAL"
        elif "HIGH" in severity_map:
            overall_severity = "HIGH"
        elif "MEDIUM" in severity_map:
            overall_severity = "MEDIUM"

        message = f"Found {len(findings)} risky policies"
        return CheckResult(
            severity=overall_severity,
            title="Risky IAM Policies Detected",
            message=message,
            details=details,
            suggested_action="Review and restrict overly-permissive policies",
        )

    def _analyze_policy_document(
        self, policy_doc: Dict[str, Any], entity: str, entity_type: str
    ) -> List[Dict[str, Any]]:
        """Analyze a single policy document for risky patterns."""
        findings = []
        statements = policy_doc.get("Statement", [])

        for statement in statements:
            effect = statement.get("Effect", "Allow")
            actions = self._normalize_actions(statement.get("Action", []))
            resources = self._normalize_resources(statement.get("Resource", []))
            not_actions = self._normalize_actions(statement.get("NotAction", []))

            # Check 1: Action: "*" with Resource: "*"
            if "*" in actions and "*" in resources and effect == "Allow":
                findings.append(
                    {
                        "entity": entity,
                        "entity_type": entity_type,
                        "severity": "CRITICAL",
                        "issue": 'Action: "*" with Resource: "*"',
                        "remediation": "Remove or restrict to specific actions and resources",
                    }
                )
                continue

            # Check 2: Wildcard actions (iam:*, ec2:*, etc.)
            for action in actions:
                if action in self.RISKY_ACTIONS:
                    findings.append(
                        {
                            "entity": entity,
                            "entity_type": entity_type,
                            "severity": self.RISKY_ACTIONS[action],
                            "issue": f'Action: "{action}"',
                            "remediation": f"Restrict to specific {action.split(':')[0]} actions",
                        }
                    )
                    break

            # Check 3: S3 GetObject with wildcard resource
            if "s3:GetObject" in actions and "*" in resources:
                findings.append(
                    {
                        "entity": entity,
                        "entity_type": entity_type,
                        "severity": "HIGH",
                        "issue": 'S3 GetObject with Resource: "*"',
                        "remediation": "Restrict to specific S3 buckets and prefixes",
                    }
                )

            # Check 4: NotAction (overly permissive)
            if not_actions and effect == "Deny":
                findings.append(
                    {
                        "entity": entity,
                        "entity_type": entity_type,
                        "severity": "MEDIUM",
                        "issue": "NotAction with Deny effect (overly broad)",
                        "remediation": "Use explicit Allow statements with specific actions",
                    }
                )

        return findings

    @staticmethod
    def _normalize_actions(action_input: Any) -> List[str]:
        """Normalize action input to list of strings."""
        if isinstance(action_input, str):
            return [action_input]
        elif isinstance(action_input, list):
            return action_input
        return []

    @staticmethod
    def _normalize_resources(resource_input: Any) -> List[str]:
        """Normalize resource input to list of strings."""
        if isinstance(resource_input, str):
            return [resource_input]
        elif isinstance(resource_input, list):
            return resource_input
        return []
