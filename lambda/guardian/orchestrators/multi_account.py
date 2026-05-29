"""Multi-Account Orchestration - Cross-account remediation and threat correlation."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio


class MultiAccountOrchestrator:
    """Orchestrate remediation across multiple AWS accounts."""

    def __init__(self, audit_logger=None, max_workers: int = 5):
        """Initialize orchestrator with account registry and thread pool."""
        self.audit = audit_logger
        self.max_workers = max_workers
        self.account_registry = {}
        self.cross_account_correlations = {}
        self.execution_results = []

    def register_account(self, account_id: str, assumed_role_arn: str, region: str = 'us-east-1') -> Dict:
        """
        Register an AWS account for cross-account operations.

        Args:
            account_id: AWS account ID (12 digits)
            assumed_role_arn: IAM role ARN to assume in target account
            region: AWS region for this account

        Returns:
            {
                'account_id': str,
                'assumed_role_arn': str,
                'region': str,
                'status': 'registered|failed',
                'timestamp': str
            }
        """
        self.account_registry[account_id] = {
            'account_id': account_id,
            'assumed_role_arn': assumed_role_arn,
            'region': region,
            'registered_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'credentials_cached': False
        }

        return {
            'account_id': account_id,
            'assumed_role_arn': assumed_role_arn,
            'region': region,
            'status': 'registered',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def assume_role(self, account_id: str, session_duration_seconds: int = 3600) -> Dict:
        """
        Assume role in target account using STS.

        Args:
            account_id: Target account ID
            session_duration_seconds: Duration of assumed role session (900-43200)

        Returns:
            {
                'account_id': str,
                'access_key_id': str,
                'secret_access_key': str,
                'session_token': str,
                'expiration': str,
                'assumed_role_arn': str,
                'status': 'success|failed'
            }
        """
        if account_id not in self.account_registry:
            return {
                'account_id': account_id,
                'status': 'failed',
                'error': f'Account {account_id} not registered'
            }

        account_info = self.account_registry[account_id]
        role_arn = account_info['assumed_role_arn']

        # Simulate STS assume role
        return {
            'account_id': account_id,
            'assumed_role_arn': role_arn,
            'access_key_id': f'ASIAIOSFODNN7EXAMPLE_{account_id}',
            'secret_access_key': f'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'session_token': f'AQoDYXdzEJr..',
            'expiration': self._get_expiration(session_duration_seconds),
            'status': 'success'
        }

    def execute_parallel_remediation(self, threats: List[Dict], account_ids: Optional[List[str]] = None) -> Dict:
        """
        Execute remediation in parallel across multiple accounts.

        Args:
            threats: List of threats to remediate
            account_ids: Accounts to target (None = all registered)

        Returns:
            {
                'total_threats': int,
                'total_accounts': int,
                'successful_remediations': int,
                'failed_remediations': int,
                'results_by_account': {
                    'account_id': [{remediation results}]
                },
                'execution_time_seconds': float
            }
        """
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)

        # Determine target accounts
        target_accounts = account_ids or list(self.account_registry.keys())
        results_by_account = {}

        # Execute remediation in parallel across accounts
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            for account_id in target_accounts:
                future = executor.submit(
                    self._remediate_account,
                    account_id,
                    threats
                )
                futures[future] = account_id

            # Collect results as they complete
            for future in as_completed(futures):
                account_id = futures[future]
                try:
                    account_results = future.result()
                    results_by_account[account_id] = account_results
                except Exception as e:
                    results_by_account[account_id] = {
                        'status': 'failed',
                        'error': str(e),
                        'remediation_results': []
                    }

        # Aggregate results
        total_successful = sum(
            len([r for r in results.get('remediation_results', []) if r.get('status') == 'success'])
            for results in results_by_account.values()
        )

        total_failed = sum(
            len([r for r in results.get('remediation_results', []) if r.get('status') == 'failed'])
            for results in results_by_account.values()
        )

        execution_time = (datetime.now(timezone.utc).replace(tzinfo=None) - start_time).total_seconds()

        self.execution_results.append({
            'total_accounts': len(target_accounts),
            'total_threats': len(threats),
            'successful': total_successful,
            'failed': total_failed,
            'execution_time': execution_time,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        })

        return {
            'total_threats': len(threats),
            'total_accounts': len(target_accounts),
            'successful_remediations': total_successful,
            'failed_remediations': total_failed,
            'results_by_account': results_by_account,
            'execution_time_seconds': round(execution_time, 2)
        }

    def correlate_cross_account_threats(self, threats_by_account: Dict[str, List[Dict]]) -> Dict:
        """
        Correlate threats across multiple accounts to identify coordinated attacks.

        Args:
            threats_by_account: Dict mapping account_id to list of threats

        Returns:
            {
                'total_accounts': int,
                'total_threats': int,
                'correlation_groups': [
                    {
                        'group_id': str,
                        'threat_signature': str,
                        'accounts_affected': [account_id],
                        'threat_count': int,
                        'severity_level': int,
                        'attack_pattern': str
                    }
                ]
            }
        """
        correlation_groups = []
        threat_signatures = {}

        # Group threats by signature across accounts
        for account_id, threats in threats_by_account.items():
            for threat in threats:
                sig = threat.get('threat_signature', 'unknown')

                if sig not in threat_signatures:
                    threat_signatures[sig] = {
                        'signature': sig,
                        'accounts': set(),
                        'threats': [],
                        'severities': [],
                        'attack_patterns': set()
                    }

                threat_signatures[sig]['accounts'].add(account_id)
                threat_signatures[sig]['threats'].append(threat)
                threat_signatures[sig]['severities'].append(threat.get('severity', 5))
                threat_signatures[sig]['attack_patterns'].add(threat.get('threat_type', 'unknown'))

        # Create correlation groups for multi-account threats
        for sig, data in threat_signatures.items():
            if len(data['accounts']) > 1:  # Multi-account threat
                group = {
                    'group_id': f"CORR-{len(correlation_groups):04d}",
                    'threat_signature': sig,
                    'accounts_affected': sorted(list(data['accounts'])),
                    'threat_count': len(data['threats']),
                    'severity_level': max(data['severities']) if data['severities'] else 5,
                    'attack_pattern': ', '.join(sorted(data['attack_patterns'])),
                    'is_coordinated': True if len(data['accounts']) >= 3 else False
                }
                correlation_groups.append(group)

        # Sort by severity and account count
        correlation_groups.sort(
            key=lambda x: (x['severity_level'], len(x['accounts_affected'])),
            reverse=True
        )

        total_threats = sum(len(threats) for threats in threats_by_account.values())

        return {
            'total_accounts': len(threats_by_account),
            'total_threats': total_threats,
            'multi_account_threat_groups': len(correlation_groups),
            'correlation_groups': correlation_groups,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def assess_cross_account_blast_radius(self, threat: Dict, affected_accounts: List[str]) -> Dict:
        """
        Assess blast radius of a threat spanning multiple accounts.

        Args:
            threat: Threat object
            affected_accounts: List of account IDs affected

        Returns:
            {
                'threat_id': str,
                'accounts_affected': int,
                'total_resources': int,
                'blast_radius_score': float,
                'risk_level': str,
                'impact_summary': str,
                'recommendations': [str]
            }
        """
        account_count = len(affected_accounts)
        base_score = threat.get('blast_radius_score', 0) / 10.0

        # Multi-account multiplier (increases risk significantly)
        account_multiplier = 1.0 + (account_count - 1) * 0.5

        # Cross-account blast radius
        cross_account_score = min(10.0, base_score * account_multiplier * 10)

        # Risk level determination
        if account_count >= 5 and threat.get('severity', 5) >= 8:
            risk_level = 'critical'
        elif account_count >= 3 and threat.get('severity', 5) >= 7:
            risk_level = 'high'
        elif account_count >= 2:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        # Impact summary
        impact = f"Threat affects {account_count} AWS accounts with {account_count * threat.get('affected_resources', 1)} total resources"

        # Recommendations
        recommendations = []
        if account_count >= 5:
            recommendations.append("Immediate cross-account incident response activation")
            recommendations.append("Notify AWS security team")
        if threat.get('severity', 5) >= 9:
            recommendations.append("Escalate to C-level leadership")
        recommendations.append(f"Isolate all {account_count} affected accounts")
        recommendations.append("Enable CloudTrail logging across all affected accounts")
        recommendations.append("Review cross-account IAM roles for compromise")

        return {
            'threat_id': threat.get('threat_id'),
            'accounts_affected': account_count,
            'total_resources': account_count * threat.get('affected_resources', 1),
            'blast_radius_score': round(cross_account_score, 2),
            'risk_level': risk_level,
            'impact_summary': impact,
            'recommendations': recommendations,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def get_cross_account_summary(self) -> Dict:
        """Get summary of cross-account operations and threats."""
        if not self.execution_results:
            return {
                'total_executions': 0,
                'total_accounts_targeted': 0,
                'total_threats_remediated': 0,
                'total_successful': 0,
                'total_failed': 0,
                'average_execution_time_seconds': 0.0,
                'success_rate': 0.0
            }

        total_accounts = sum(r['total_accounts'] for r in self.execution_results)
        total_threats = sum(r['total_threats'] for r in self.execution_results)
        total_successful = sum(r['successful'] for r in self.execution_results)
        total_failed = sum(r['failed'] for r in self.execution_results)
        avg_execution_time = sum(r['execution_time'] for r in self.execution_results) / len(self.execution_results)

        success_rate = total_successful / (total_successful + total_failed) if (total_successful + total_failed) > 0 else 0.0

        return {
            'total_executions': len(self.execution_results),
            'total_accounts_targeted': total_accounts,
            'total_threats_remediated': total_threats,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'average_execution_time_seconds': round(avg_execution_time, 2),
            'success_rate': round(success_rate, 3)
        }

    def _remediate_account(self, account_id: str, threats: List[Dict]) -> Dict:
        """Execute remediation for a single account."""
        # Simulate account-specific remediation
        results = []
        for threat in threats:
            result = {
                'threat_id': threat.get('threat_id'),
                'account_id': account_id,
                'status': 'success' if threat.get('severity', 5) < 9 else 'success',
                'remediation_type': threat.get('remediation_type', 'unknown'),
                'duration_seconds': 30.0 + threat.get('affected_resources', 1) * 5.0
            }
            results.append(result)

        return {
            'account_id': account_id,
            'status': 'completed',
            'remediation_results': results,
            'total_remediated': len(results),
            'successful_count': sum(1 for r in results if r['status'] == 'success'),
            'failed_count': sum(1 for r in results if r['status'] == 'failed')
        }

    def _get_expiration(self, duration_seconds: int) -> str:
        """Get expiration timestamp for assumed role session."""
        from datetime import timedelta
        expiration = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=duration_seconds)
        return expiration.isoformat()
