"""GLM AI-based analysis and response for AWS Guardian"""
import os
import json
import requests
from typing import Dict, Any, List, Tuple
from datetime import datetime

class GLMAnalyzer:
    """GLM-based AI analyzer for anomaly analysis and response suggestions"""

    def __init__(self, api_key: str = None):
        """
        Initialize GLM analyzer

        Args:
            api_key: Zhipu GLM API key
        """
        self.api_key = api_key or os.getenv('GLM_API_KEY', '')
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4"
        self.is_available = bool(self.api_key)

    def _make_request(self, messages: List[Dict]) -> Tuple[bool, str]:
        """Make a request to GLM API"""
        if not self.is_available:
            print("[GLM] API key not available, skipping analysis")
            return False, ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.8,
                "max_tokens": 1000
            }

            print(f"[GLM] Sending request to {self.base_url}/chat/completions")
            print(f"[GLM] Model: {self.model}")
            print(f"[GLM] Messages: {len(messages)}")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            print(f"[GLM] Response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    print(f"[GLM] Analysis successful: {len(content)} chars")
                    return True, content
                else:
                    print(f"[GLM] Unexpected response format: {result}")
                    return False, ""
            else:
                error_body = response.text
                print(f"[GLM] API error {response.status_code}: {error_body}")
                # Try to extract error message
                try:
                    error_json = response.json()
                    error_msg = error_json.get('error', {}).get('message', error_body)
                    print(f"[GLM] Error detail: {error_msg}")
                except:
                    pass
                return False, ""

        except requests.exceptions.Timeout:
            print(f"[GLM] Request timeout (30s)")
            return False, ""
        except Exception as e:
            print(f"[GLM] Request error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False, ""

    def analyze_cost_anomaly(self, cost_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze cost anomaly using GLM

        Args:
            cost_data: Cost checker result

        Returns:
            Analysis result with insights and recommendations
        """
        today_cost = cost_data.get('today_cost', 0)
        threshold = cost_data.get('threshold', 0)
        yesterday_cost = cost_data.get('yesterday_cost', 0)
        monthly_cost = cost_data.get('monthly_cost', 0)
        increase_percent = cost_data.get('increase_percent', 0)

        prompt = f"""AWS 비용 급증 분석:

오늘 비용: ${today_cost:.2f}
임계값: ${threshold:.2f}
어제 비용: ${yesterday_cost:.2f}
월간 비용: ${monthly_cost:.2f}
증가율: {increase_percent}%

분석 항목:
1. 심각도 (low/medium/high/critical)
2. 근본 원인
3. 즉시 조치
4. 장기 최적화

JSON 형식으로 응답."""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        print(f"[GLM] Analyzing cost anomaly: ${today_cost:.2f}")
        success, response = self._make_request(messages)

        if success:
            try:
                # Try to parse as JSON
                analysis = {}
                if response.startswith('{'):
                    analysis = json.loads(response)
                else:
                    # Extract JSON from response
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        try:
                            analysis = json.loads(response[start:end])
                        except json.JSONDecodeError:
                            analysis = {'raw_response': response[start:end]}
                    else:
                        analysis = {
                            'severity': 'medium',
                            'analysis': response,
                            'recommendations': []
                        }
                return {
                    'success': True,
                    'analysis': analysis,
                    'timestamp': datetime.utcnow().isoformat()
                }
            except json.JSONDecodeError as e:
                print(f"[GLM] JSON parse error: {e}")
                return {
                    'success': True,
                    'analysis': {'raw_response': response},
                    'timestamp': datetime.utcnow().isoformat()
                }
        else:
            print("[GLM] Cost analysis failed")
            return {
                'success': False,
                'analysis': {'error': 'GLM analysis unavailable'},
                'timestamp': datetime.utcnow().isoformat()
            }

    def analyze_ec2_anomalies(self, ec2_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze EC2 security anomalies using GLM

        Args:
            ec2_data: EC2 checker result

        Returns:
            Analysis result with security assessment
        """
        unauthorized = ec2_data.get('unauthorized_region_instances', {})
        exposed = ec2_data.get('exposed_instances', [])
        new_instances = ec2_data.get('new_instances', [])

        anomalies_str = f"""
EC2 Security Anomalies Detected:

Unauthorized Regions: {len(unauthorized)} instances
Exposed to 0.0.0.0/0: {len(exposed)} instances
New Instances: {len(new_instances)}

Details:
- Unauthorized regions: {list(unauthorized.keys()) if unauthorized else 'None'}
- Exposed instances: {[inst['instance_id'] for inst in exposed[:3]]}
- New instances: {[inst['instance_id'] for inst in new_instances[:3]]}
"""

        prompt = f"""
Analyze the following EC2 security anomalies:

{anomalies_str}

Please provide:
1. Security risk assessment (critical/high/medium/low)
2. Immediate security threats
3. Auto-response recommendations (stop instance/modify SG/etc)
4. Investigation steps
5. Prevention measures

Format as JSON with these exact keys: risk_level, threats, auto_response, investigation, prevention
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        success, response = self._make_request(messages)

        if success:
            try:
                if response.startswith('{'):
                    analysis = json.loads(response)
                else:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(response[start:end])
                    else:
                        analysis = {'raw_response': response}
                return {
                    'success': True,
                    'analysis': analysis,
                    'timestamp': datetime.utcnow().isoformat()
                }
            except json.JSONDecodeError:
                return {
                    'success': True,
                    'analysis': {'raw_response': response},
                    'timestamp': datetime.utcnow().isoformat()
                }
        else:
            return {
                'success': False,
                'analysis': {'error': 'GLM analysis unavailable'},
                'timestamp': datetime.utcnow().isoformat()
            }

    def analyze_s3_anomalies(self, s3_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze S3 security anomalies using GLM

        Args:
            s3_data: S3 checker result

        Returns:
            Analysis result with compliance assessment
        """
        public_buckets = s3_data.get('public_buckets', [])
        new_buckets = s3_data.get('new_buckets', [])

        anomalies_str = f"""
S3 Security Anomalies Detected:

Public Buckets: {len(public_buckets)}
New Buckets: {len(new_buckets)}

Public Buckets Details:
{json.dumps([{'name': b['bucket_name'], 'reasons': b['public_reasons']} for b in public_buckets[:5]], indent=2)}

New Buckets:
{json.dumps([b['bucket_name'] for b in new_buckets[:5]], indent=2)}
"""

        prompt = f"""
Analyze the following S3 security anomalies:

{anomalies_str}

Please provide:
1. Compliance risk level (critical/high/medium/low)
2. Data exposure risks
3. Recommended actions (block public access, bucket policies, etc)
4. Audit recommendations
5. Encryption recommendations

Format as JSON with keys: compliance_risk, exposure_risks, actions, audit, encryption
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        success, response = self._make_request(messages)

        if success:
            try:
                if response.startswith('{'):
                    analysis = json.loads(response)
                else:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(response[start:end])
                    else:
                        analysis = {'raw_response': response}
                return {
                    'success': True,
                    'analysis': analysis,
                    'timestamp': datetime.utcnow().isoformat()
                }
            except json.JSONDecodeError:
                return {
                    'success': True,
                    'analysis': {'raw_response': response},
                    'timestamp': datetime.utcnow().isoformat()
                }
        else:
            return {
                'success': False,
                'analysis': {'error': 'GLM analysis unavailable'},
                'timestamp': datetime.utcnow().isoformat()
            }

    def generate_summary_report(self, all_checks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered summary report using GLM

        Args:
            all_checks: All check results

        Returns:
            Summary report with insights
        """
        summary_prompt = f"""
Generate an executive summary of AWS account security and cost status based on this data:

Cost Check:
- Today: ${all_checks.get('cost', {}).get('today_cost', 0):.2f}
- Monthly: ${all_checks.get('cost', {}).get('monthly_cost', 0):.2f}
- Status: {'⚠️ ANOMALY' if all_checks.get('cost', {}).get('is_anomaly') else '✅ NORMAL'}

EC2 Status:
- Security Issues: {len(all_checks.get('ec2', {}).get('anomalies', []))}
- Exposed Instances: {len(all_checks.get('ec2', {}).get('exposed_instances', []))}

S3 Status:
- Public Buckets: {len(all_checks.get('s3', {}).get('public_buckets', []))}
- New Buckets: {len(all_checks.get('s3', {}).get('new_buckets', []))}

Please provide:
1. Overall security posture (critical/high/medium/low risk)
2. Top 3 priorities for remediation
3. Cost optimization opportunities
4. Compliance status
5. Executive summary (2-3 sentences)

Format as JSON
"""

        messages = [
            {
                "role": "user",
                "content": summary_prompt
            }
        ]

        success, response = self._make_request(messages)

        if success:
            try:
                if response.startswith('{'):
                    report = json.loads(response)
                else:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        report = json.loads(response[start:end])
                    else:
                        report = {'summary': response}
                return {
                    'success': True,
                    'report': report,
                    'timestamp': datetime.utcnow().isoformat()
                }
            except json.JSONDecodeError:
                return {
                    'success': True,
                    'report': {'summary': response},
                    'timestamp': datetime.utcnow().isoformat()
                }
        else:
            return {
                'success': False,
                'report': {'error': 'GLM analysis unavailable'},
                'timestamp': datetime.utcnow().isoformat()
            }

    def get_remediation_steps(self, issue_type: str, issue_details: Dict[str, Any]) -> List[str]:
        """
        Get step-by-step remediation instructions from GLM

        Args:
            issue_type: Type of issue (cost_anomaly, ec2_exposure, s3_public, etc)
            issue_details: Issue details

        Returns:
            List of remediation steps
        """
        prompt = f"""
Provide step-by-step remediation instructions for the following AWS issue:

Issue Type: {issue_type}
Details: {json.dumps(issue_details, indent=2)}

Please provide:
- Clear, numbered steps
- AWS CLI commands where applicable
- Expected outcomes
- Verification steps

Format as JSON with key "steps" containing a list of strings.
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        success, response = self._make_request(messages)

        if success:
            try:
                if response.startswith('{'):
                    result = json.loads(response)
                else:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        result = json.loads(response[start:end])
                    else:
                        return [response]

                steps = result.get('steps', [])
                return steps if isinstance(steps, list) else [str(steps)]
            except json.JSONDecodeError:
                return [response]
        else:
            return ["GLM analysis unavailable"]
