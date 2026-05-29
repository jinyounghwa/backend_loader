"""Network Isolation Auto-Remediation - Isolate compromised instances via Security Groups."""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum


class RemediationStatus(Enum):
    """Remediation outcome statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class NetworkRemediator:
    """Automatic remediation for unauthorized network access."""

    # Critical ports that must NOT be blocked
    CRITICAL_PORTS = {22, 3389}  # SSH, RDP

    def __init__(self, ec2_client, audit_logger):
        """Initialize network remediation with AWS client and audit logger."""
        self.ec2 = ec2_client
        self.audit = audit_logger
        self.remediation_history = {}

    def remediate_unauthorized_access(self, instance_id: str, threat: Dict) -> Dict:
        """
        Remove unauthorized security group rules from instance.

        Args:
            instance_id: EC2 instance ID
            threat: Threat detection details

        Returns:
            {
                'status': 'success|skipped|failed',
                'instance_id': instance_id,
                'rules_removed': int,
                'rules_preserved': int,
                'timestamp': iso_timestamp
            }
        """
        result = {
            'instance_id': instance_id,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'threat': threat.get('threat_id', 'unknown'),
            'rules_removed': 0,
            'rules_preserved': 0
        }

        try:
            # Get instance details
            instance = self._get_instance_details(instance_id)
            security_groups = instance.get('SecurityGroups', [])

            total_rules_removed = 0

            for sg in security_groups:
                sg_id = sg.get('GroupId')
                sg_details = self.ec2.describe_security_groups(GroupIds=[sg_id])
                ingress_rules = sg_details.get('SecurityGroups', [{}])[0].get('IpPermissions', [])

                # Remove public access rules
                for rule in ingress_rules:
                    if self._is_public_access_rule(rule):
                        self._remove_security_group_rule(sg_id, rule, 'ingress')
                        total_rules_removed += 1
                    else:
                        result['rules_preserved'] += 1

            result['rules_removed'] = total_rules_removed
            result['status'] = RemediationStatus.SUCCESS.value
            result['action_taken'] = 'removed' if total_rules_removed > 0 else 'none_needed'

            # Audit log
            self.audit.log_remediation(instance_id, result)

        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['error'] = str(e)

        return result

    def isolate_instance(self, instance_id: str, threat: Dict) -> Dict:
        """
        Create restricted security group and apply to instance.

        Args:
            instance_id: EC2 instance ID
            threat: Threat detection details

        Returns:
            {
                'status': 'success|skipped|failed',
                'instance_id': instance_id,
                'original_security_groups': [sg_ids],
                'new_security_group_id': sg_id,
                'timestamp': iso_timestamp
            }
        """
        result = {
            'instance_id': instance_id,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'threat': threat.get('threat_id', 'unknown')
        }

        try:
            # Get instance and VPC
            instance = self._get_instance_details(instance_id)
            vpc_id = instance.get('VpcId')
            original_sgs = [sg.get('GroupId') for sg in instance.get('SecurityGroups', [])]

            # Create isolated security group
            isolated_sg = self.ec2.create_security_group(
                GroupName=f'isolated-{instance_id[:8]}',
                Description=f'Isolation SG for {instance_id}',
                VpcId=vpc_id
            )
            new_sg_id = isolated_sg['GroupId']

            # Apply new SG (replace existing)
            self.ec2.modify_instance_attribute(
                InstanceId=instance_id,
                Groups=[new_sg_id]
            )

            # Store original SGs for rollback
            self.remediation_history[instance_id] = {
                'original_groups': original_sgs,
                'isolated_group': new_sg_id,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }

            result['status'] = RemediationStatus.SUCCESS.value
            result['action_taken'] = 'isolated'
            result['original_security_groups'] = original_sgs
            result['new_security_group_id'] = new_sg_id

            # Audit log
            self.audit.log_remediation(instance_id, result)

        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['error'] = str(e)

        return result

    def restore_connectivity(self, instance_id: str) -> Dict:
        """
        Restore original security groups (rollback isolation).

        Args:
            instance_id: EC2 instance ID

        Returns:
            {
                'status': 'success|skipped|failed',
                'instance_id': instance_id,
                'restored_groups': [sg_ids],
                'timestamp': iso_timestamp
            }
        """
        result = {
            'instance_id': instance_id,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        try:
            if instance_id not in self.remediation_history:
                result['status'] = RemediationStatus.SKIPPED.value
                result['reason'] = 'No isolation history found'
                return result

            history = self.remediation_history[instance_id]
            original_groups = history.get('original_groups', [])

            # Restore original security groups
            self.ec2.modify_instance_attribute(
                InstanceId=instance_id,
                Groups=original_groups
            )

            # Delete isolated security group
            isolated_sg_id = history.get('isolated_group')
            try:
                self.ec2.delete_security_group(GroupId=isolated_sg_id)
            except Exception:
                pass  # SG might be in use, ignore

            result['status'] = RemediationStatus.SUCCESS.value
            result['action_taken'] = 'restored'
            result['restored_groups'] = original_groups

            # Clean up history
            del self.remediation_history[instance_id]

            # Audit log
            self.audit.log_remediation(instance_id, result)

        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['error'] = str(e)

        return result

    def _get_instance_details(self, instance_id: str) -> Dict:
        """Get EC2 instance details."""
        response = self.ec2.describe_instances(InstanceIds=[instance_id])
        instances = response.get('Reservations', [{}])[0].get('Instances', [])
        if not instances:
            raise ValueError(f'Instance {instance_id} not found')
        return instances[0]

    def _is_public_access_rule(self, rule: Dict) -> bool:
        """Check if rule allows public access (0.0.0.0/0)."""
        for ip_range in rule.get('IpRanges', []):
            if ip_range.get('CidrIp') == '0.0.0.0/0':
                from_port = rule.get('FromPort', 0)
                to_port = rule.get('ToPort', 65535)

                # Allow critical ports
                if from_port <= min(self.CRITICAL_PORTS) <= to_port:
                    if to_port >= max(self.CRITICAL_PORTS):
                        continue

                return True

        for ipv6_range in rule.get('Ipv6Ranges', []):
            if ipv6_range.get('CidrIpv6') == '::/0':
                return True

        return False

    def _remove_security_group_rule(self, sg_id: str, rule: Dict, direction: str = 'ingress'):
        """Remove a security group rule."""
        try:
            if direction == 'ingress':
                self.ec2.revoke_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[rule]
                )
            else:
                self.ec2.revoke_security_group_egress(
                    GroupId=sg_id,
                    IpPermissions=[rule]
                )
        except Exception:
            pass  # Rule might not exist, ignore

    def verify_critical_ports(self, instance_id: str) -> Dict:
        """Verify critical ports are not blocked."""
        result = {
            'instance_id': instance_id,
            'critical_ports_blocked': [],
            'checks': {}
        }

        try:
            instance = self._get_instance_details(instance_id)
            sgs = instance.get('SecurityGroups', [])

            for sg in sgs:
                sg_id = sg.get('GroupId')
                sg_details = self.ec2.describe_security_groups(GroupIds=[sg_id])
                ingress_rules = sg_details.get('SecurityGroups', [{}])[0].get('IpPermissions', [])

                for rule in ingress_rules:
                    from_port = rule.get('FromPort', 0)
                    to_port = rule.get('ToPort', 65535)

                    for port in self.CRITICAL_PORTS:
                        if from_port <= port <= to_port:
                            result['checks'][f'port_{port}_accessible'] = True
                        else:
                            result['checks'][f'port_{port}_blocked'] = True

            result['status'] = 'passed' if not result['critical_ports_blocked'] else 'failed'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result
