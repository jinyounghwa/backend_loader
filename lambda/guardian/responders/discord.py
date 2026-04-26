"""Discord notification responder for AWS Guardian"""
import requests
import json
import os
from typing import Dict, Any

class DiscordResponder:
    def __init__(self, webhook_url: str = None):
        """
        Initialize Discord responder

        Args:
            webhook_url: Discord webhook URL for notifications
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')

    def send_embed(self, embed: Dict[str, Any]) -> bool:
        """Send an embed message to Discord"""
        try:
            response = requests.post(
                self.webhook_url,
                json={'embeds': [embed]},
                timeout=10
            )
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error sending Discord embed: {e}")
            return False

    def send_cost_alert(self, cost_data: Dict[str, Any]) -> bool:
        """Send cost anomaly alert as Discord embed"""
        today_cost = cost_data.get('today_cost', 0)
        threshold = cost_data.get('threshold', 0)
        increase_percent = cost_data.get('increase_percent', 0)

        embed = {
            'title': '💰 AWS Cost Alert',
            'color': 16711680,  # Red
            'fields': [
                {
                    'name': "Today's Cost",
                    'value': f"${today_cost:.2f}",
                    'inline': True
                },
                {
                    'name': 'Threshold',
                    'value': f"${threshold:.2f}",
                    'inline': True
                },
                {
                    'name': 'Increase',
                    'value': f'{increase_percent}%',
                    'inline': True
                },
                {
                    'name': 'Date',
                    'value': cost_data.get('date', 'N/A'),
                    'inline': True
                },
                {
                    'name': "Yesterday's Cost",
                    'value': f"${cost_data.get('yesterday_cost', 0):.2f}",
                    'inline': True
                },
                {
                    'name': 'Monthly Cost',
                    'value': f"${cost_data.get('monthly_cost', 0):.2f}",
                    'inline': True
                }
            ],
            'description': '⚠️ Cost threshold exceeded!',
            'footer': {'text': 'AWS Guardian'}
        }

        return self.send_embed(embed)

    def send_ec2_alert(self, ec2_data: Dict[str, Any]) -> bool:
        """Send EC2 security alert as Discord embed"""
        fields = []

        # Unauthorized regions
        unauthorized = ec2_data.get('unauthorized_region_instances', {})
        if unauthorized:
            regions_list = ', '.join(unauthorized.keys())
            total_instances = sum(len(insts) for insts in unauthorized.values())
            fields.append({
                'name': '🌍 Unauthorized Region Instances',
                'value': f'{regions_list} ({total_instances} instances)',
                'inline': False
            })

        # Exposed instances
        exposed = ec2_data.get('exposed_instances', [])
        if exposed:
            exposed_list = '\n'.join([
                f"• {exp['instance_id']} ({exp['region']})"
                for exp in exposed[:5]
            ])
            fields.append({
                'name': '🔓 Exposed to 0.0.0.0/0',
                'value': exposed_list,
                'inline': False
            })

        # New instances
        new = ec2_data.get('new_instances', [])
        if new:
            new_list = '\n'.join([
                f"• {inst['instance_id']} ({inst['region']})"
                for inst in new[:5]
            ])
            fields.append({
                'name': f'🆕 New Instances ({len(new)})',
                'value': new_list,
                'inline': False
            })

        embed = {
            'title': '⚠️ EC2 Security Alert',
            'color': 16776960,  # Yellow
            'fields': fields,
            'description': '🔒 Automated response: Stopping instances...',
            'footer': {'text': 'AWS Guardian'}
        }

        return self.send_embed(embed)

    def send_s3_alert(self, s3_data: Dict[str, Any]) -> bool:
        """Send S3 security alert as Discord embed"""
        fields = []

        # Public buckets
        public = s3_data.get('public_buckets', [])
        if public:
            public_list = '\n'.join([
                f"• {bucket['bucket_name']}\n  └ {', '.join(bucket['public_reasons'])}"
                for bucket in public[:3]
            ])
            fields.append({
                'name': f'🌐 Public Buckets ({len(public)})',
                'value': public_list,
                'inline': False
            })

        # New buckets
        new = s3_data.get('new_buckets', [])
        if new:
            new_list = '\n'.join([
                f"• {bucket['bucket_name']}"
                for bucket in new[:5]
            ])
            fields.append({
                'name': f'🆕 New Buckets ({len(new)})',
                'value': new_list,
                'inline': False
            })

        embed = {
            'title': '🔐 S3 Security Alert',
            'color': 16711680,  # Red
            'fields': fields,
            'description': '⚡ Automated response: Blocking public access...',
            'footer': {'text': 'AWS Guardian'}
        }

        return self.send_embed(embed)

    def send_status_embed(self, status_data: Dict[str, Any]) -> bool:
        """Send current status as Discord embed"""
        fields = [
            {
                'name': '💰 Monthly Cost',
                'value': f"${status_data.get('monthly_cost', 0):.2f}",
                'inline': True
            },
            {
                'name': '🏃 Running EC2',
                'value': str(status_data.get('running_instances', 0)),
                'inline': True
            },
            {
                'name': '🪣 S3 Buckets',
                'value': str(status_data.get('total_buckets', 0)),
                'inline': True
            }
        ]

        embed = {
            'title': '📊 AWS Guardian Status',
            'color': 65280,  # Green
            'fields': fields,
            'footer': {'text': 'AWS Guardian'}
        }

        return self.send_embed(embed)

    def send_summary_embed(self, summary_data: Dict[str, Any]) -> bool:
        """Send daily summary as Discord embed"""
        total = summary_data.get('total_events', 0)
        by_type = summary_data.get('by_type', {})
        by_severity = summary_data.get('by_severity', {})

        fields = []

        # By type
        type_str = '\n'.join([f"• {k}: {v}" for k, v in by_type.items()])
        fields.append({
            'name': 'Events by Type',
            'value': type_str or 'None',
            'inline': False
        })

        # By severity
        severity_str = '\n'.join([f"• {k}: {v}" for k, v in by_severity.items()])
        fields.append({
            'name': 'Events by Severity',
            'value': severity_str or 'None',
            'inline': False
        })

        embed = {
            'title': '📊 AWS Guardian Daily Summary',
            'color': 5814783,  # Blue
            'description': f'Total Events: {total}',
            'fields': fields,
            'footer': {'text': 'AWS Guardian'}
        }

        return self.send_embed(embed)
