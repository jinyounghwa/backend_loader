"""Predictive cost optimization: Instance sizing, RI recommendations, Spot strategy"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InstanceSizer:
    """Recommend right-sized EC2 instances."""

    def __init__(self):
        self.instance_types = {
            't3.nano': {'cpu': 2, 'memory': 0.5, 'monthly_cost': 4},
            't3.micro': {'cpu': 2, 'memory': 1, 'monthly_cost': 8},
            't3.small': {'cpu': 2, 'memory': 2, 'monthly_cost': 16},
            't3.medium': {'cpu': 2, 'memory': 4, 'monthly_cost': 32},
            't3.large': {'cpu': 2, 'memory': 8, 'monthly_cost': 65},
            't3.xlarge': {'cpu': 4, 'memory': 16, 'monthly_cost': 131},
            'm5.large': {'cpu': 2, 'memory': 8, 'monthly_cost': 96},
            'c5.large': {'cpu': 2, 'memory': 4, 'monthly_cost': 85},
        }

    def recommend(self, current: Dict) -> Dict:
        """Recommend right-sized instance."""
        current_type = current.get('type', 't3.xlarge')
        current_cost = current.get('monthly_cost', 131)
        cpu_usage = current.get('avg_cpu_usage', 50)
        memory_usage = current.get('avg_memory_usage', 50)

        current_spec = self.instance_types.get(current_type, {})
        current_vcpu = current_spec.get('cpu', 4)
        current_memory = current_spec.get('memory', 16)

        required_vcpu = (cpu_usage / 100) * current_vcpu * 1.2
        required_memory = (memory_usage / 100) * current_memory * 1.2

        best_fit = None
        best_cost = current_cost
        savings = 0

        for itype, spec in self.instance_types.items():
            if spec['cpu'] >= required_vcpu and spec['memory'] >= required_memory:
                if spec['monthly_cost'] < best_cost:
                    best_fit = itype
                    best_cost = spec['monthly_cost']
                    savings = current_cost - best_cost

        if best_fit is None:
            return {
                'current_type': current_type,
                'recommended_type': current_type,
                'current_cost': current_cost,
                'recommended_cost': current_cost,
                'monthly_savings': 0,
                'action': 'no_change'
            }

        return {
            'current_type': current_type,
            'recommended_type': best_fit,
            'current_cost': current_cost,
            'recommended_cost': best_cost,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'action': 'resize'
        }


class RIPurchaseAdvisor:
    """Recommend Reserved Instance purchases."""

    def __init__(self):
        self.ri_discount_rates = {
            'one_year': 0.33,
            'three_year': 0.50,
        }

    def recommend_ri_purchases(self, instances: List[Dict]) -> List[Dict]:
        """Recommend RI purchases."""
        recommendations = []

        for instance in instances:
            itype = instance.get('type', 't3.medium')
            monthly_cost = instance.get('monthly_cost', 32)
            uptime_percentage = instance.get('uptime_percentage', 80)

            if uptime_percentage < 70:
                continue

            one_year_upfront = monthly_cost * 12 * (1 - self.ri_discount_rates['one_year'])
            three_year_upfront = monthly_cost * 36 * (1 - self.ri_discount_rates['three_year'])

            recommendations.append({
                'instance_type': itype,
                'uptime_percentage': uptime_percentage,
                'one_year_upfront': one_year_upfront,
                'one_year_savings': monthly_cost * 12 - one_year_upfront,
                'three_year_upfront': three_year_upfront,
                'three_year_savings': monthly_cost * 36 - three_year_upfront,
                'recommended_term': 'three_year'
            })

        return recommendations


class SpotInstanceStrategy:
    """Recommend Spot instance usage."""

    def __init__(self):
        self.spot_discount_rates = {'t3': 0.70, 'm5': 0.70, 'c5': 0.75}

    def recommend_spot_instances(self, instances: List[Dict]) -> List[Dict]:
        """Recommend Spot instance conversions."""
        recommendations = []

        for instance in instances:
            itype = instance.get('type', 't3.medium')
            family = itype.split('.')[0]
            monthly_cost = instance.get('monthly_cost', 32)

            spot_rate = self.spot_discount_rates.get(family, 0.70)
            spot_cost = monthly_cost * (1 - spot_rate)
            monthly_savings = monthly_cost - spot_cost

            recommendations.append({
                'instance_type': itype,
                'on_demand_cost': monthly_cost,
                'spot_cost': spot_cost,
                'monthly_savings': monthly_savings,
                'annual_savings': monthly_savings * 12,
                'discount_percentage': spot_rate * 100
            })

        return recommendations


    def blended_strategy(self, instances: List[Dict]) -> Dict:
        """Recommend blended Spot + On-Demand strategy."""
        total_on_demand = sum(inst.get('monthly_cost', 0) for inst in instances)
        spot_portion = total_on_demand * 0.7 * 0.70
        on_demand_portion = total_on_demand * 0.3

        total_blended = spot_portion + on_demand_portion
        monthly_savings = total_on_demand - total_blended

        return {
            'strategy': 'blended_spot_on_demand',
            'on_demand_percentage': 30,
            'spot_percentage': 70,
            'current_monthly_cost': total_on_demand,
            'blended_monthly_cost': total_blended,
            'monthly_savings': monthly_savings,
            'annual_savings': monthly_savings * 12
        }


@dataclass
class OptimizationRecommendation:
    """비용 절감 제안"""
    type: str  # 'downsize_instance', 'delete_snapshot', 'move_to_glacier', etc.
    resource_id: str
    description: str
    monthly_savings: float
    effort: str  # 'low', 'medium', 'high'
    priority: int  # 1-10
    estimated_implementation_time_hours: float


class CostOptimizer:
    """AWS 비용 절감 제안 분석 엔진"""

    def __init__(self, cost_explorer_client, ec2_client, rds_client):
        """
        Args:
            cost_explorer_client: boto3 CostExplorer client
            ec2_client: boto3 EC2 client
            rds_client: boto3 RDS client
        """
        self.explorer = cost_explorer_client
        self.ec2 = ec2_client
        self.rds = rds_client

    def analyze_cost_patterns(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        비용 패턴 분석 후 절감 기회 식별

        Args:
            account_id: AWS Account ID
            days: 분석 기간 (일)

        Returns:
            비용 절감 기회 목록
        """
        try:
            from datetime import timezone
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )

            costs = []
            for result in response.get('ResultsByTime', []):
                date = result['TimePeriod']['Start']
                cost = float(result['Total']['UnblendedCost']['Amount'])
                costs.append({'date': date, 'cost': cost})

            # 패턴 분석
            patterns = self._identify_patterns(costs)
            logger.info(f"Analyzed {len(costs)} days of cost data, found {len(patterns)} patterns")

            return patterns

        except Exception as e:
            logger.error(f"Cost pattern analysis failed: {str(e)}")
            return []

    def recommend_instance_downsizing(self, account_id: str) -> List[Dict]:
        """
        사용률 낮은 EC2 인스턴스 다운사이징 제안

        Returns:
            다운사이징 제안 목록
        """
        try:
            response = self.ec2.describe_instances()
            recommendations = []

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance['InstanceId']
                    current_type = instance['InstanceType']

                    # 실제 구현에서는 CloudWatch 메트릭으로 CPU 사용률 확인
                    # 여기서는 시뮬레이션
                    cpu_utilization = self._get_instance_cpu_utilization(instance_id)

                    if cpu_utilization and cpu_utilization < 20:
                        recommended_type = self._get_downsized_instance_type(current_type)
                        monthly_savings = self._calculate_instance_savings(current_type, recommended_type)

                        recommendations.append({
                            'instance_id': instance_id,
                            'current_type': current_type,
                            'recommended_type': recommended_type,
                            'cpu_utilization': cpu_utilization,
                            'monthly_savings': monthly_savings,
                            'priority': 'high' if monthly_savings > 500 else 'medium'
                        })

            logger.info(f"Found {len(recommendations)} EC2 downsizing opportunities")
            return recommendations

        except Exception as e:
            logger.error(f"Instance downsizing analysis failed: {str(e)}")
            return []

    def detect_overprovisioned_databases(self, account_id: str) -> List[Dict]:
        """
        과도하게 프로비저닝된 RDS 인스턴스 탐지

        Returns:
            과다 프로비저닝 인스턴스 목록
        """
        try:
            response = self.rds.describe_db_instances()
            issues = []

            for db in response.get('DBInstances', []):
                db_id = db['DBInstanceIdentifier']
                db_class = db['DBInstanceClass']

                # 실제 구현에서는 CloudWatch에서 CPU/메모리 사용률 조회
                cpu_utilization = self._get_database_cpu_utilization(db_id)
                memory_utilization = self._get_database_memory_utilization(db_id)

                if (cpu_utilization and cpu_utilization < 20 and
                    memory_utilization and memory_utilization < 30):

                    monthly_cost = self._get_database_monthly_cost(db_class)
                    recommended_class = self._get_downsized_database_class(db_class)
                    estimated_savings = monthly_cost * 0.5  # 약 50% 절감 예상

                    issues.append({
                        'database_id': db_id,
                        'current_class': db_class,
                        'recommended_class': recommended_class,
                        'cpu_utilization': cpu_utilization,
                        'memory_utilization': memory_utilization,
                        'monthly_cost': monthly_cost,
                        'estimated_savings': estimated_savings,
                        'priority': 'high'
                    })

            logger.info(f"Found {len(issues)} overprovisioned RDS instances")
            return issues

        except Exception as e:
            logger.error(f"Database analysis failed: {str(e)}")
            return []

    def analyze_storage_costs(self, account_id: str) -> List[Dict]:
        """
        S3 및 EBS 스토리지 비용 최적화 제안

        Returns:
            스토리지 최적화 제안 목록
        """
        try:
            from datetime import timezone
            today = datetime.now(timezone.utc).date()
            yesterday = today - timedelta(days=1)
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': yesterday.isoformat(),
                    'End': today.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )

            recommendations = []
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])

                    if 'Simple Storage Service' in service:
                        recommendations.append({
                            'type': 'enable_s3_lifecycle',
                            'service': service,
                            'current_cost': cost,
                            'description': 'Move old objects to cheaper storage classes',
                            'monthly_savings': cost * 0.3,
                            'priority': 'medium'
                        })
                    elif 'Elastic Block Store' in service:
                        recommendations.append({
                            'type': 'delete_unattached_volumes',
                            'service': service,
                            'current_cost': cost,
                            'description': 'Delete unattached EBS volumes',
                            'monthly_savings': cost * 0.2,
                            'priority': 'medium'
                        })

            logger.info(f"Found {len(recommendations)} storage optimization opportunities")
            return recommendations

        except Exception as e:
            logger.error(f"Storage cost analysis failed: {str(e)}")
            return []

    def get_all_recommendations(self, account_id: str) -> List[Dict]:
        """
        모든 카테고리의 비용 절감 제안 통합 조회

        Returns:
            전체 제안 목록 (우선순위 정렬)
        """
        all_recommendations = []

        # 각 분석 실행
        all_recommendations.extend(self.analyze_cost_patterns(account_id))
        all_recommendations.extend(self.recommend_instance_downsizing(account_id))
        all_recommendations.extend(self.detect_overprovisioned_databases(account_id))
        all_recommendations.extend(self.analyze_storage_costs(account_id))

        # 우선순위로 정렬
        all_recommendations.sort(
            key=lambda x: x.get('monthly_savings', 0),
            reverse=True
        )

        logger.info(f"Generated {len(all_recommendations)} total recommendations")
        return all_recommendations

    def calculate_priority_scores(self, recommendations: List[Dict]) -> List[float]:
        """
        권장사항 우선순위 점수 계산 (0-100)

        점수 = (절감액 * 0.6 + (100 - effort_score) * 0.4)

        Args:
            recommendations: 권장사항 목록

        Returns:
            우선순위 점수 목록
        """
        scores = []

        for rec in recommendations:
            monthly_savings = rec.get('monthly_savings', 0)
            effort = rec.get('effort', 'medium')

            # Effort 점수 변환
            effort_score = {'low': 20, 'medium': 50, 'high': 80}.get(effort, 50)

            # 절감액 정규화 (최대 1000으로 가정)
            savings_score = min(100, (monthly_savings / 1000) * 100)

            # 최종 점수
            priority_score = (savings_score * 0.6) + ((100 - effort_score) * 0.4)
            scores.append(min(100, max(0, priority_score)))

        return scores

    def _identify_patterns(self, costs: List[Dict]) -> List[Dict]:
        """비용 패턴 식별"""
        patterns = []

        if len(costs) < 2:
            return patterns

        # 일일 변화도 분석
        for i in range(1, len(costs)):
            change_percent = ((costs[i]['cost'] - costs[i-1]['cost']) / costs[i-1]['cost'] * 100) \
                if costs[i-1]['cost'] > 0 else 0

            if abs(change_percent) > 3:  # 3% 이상 변화
                patterns.append({
                    'date': costs[i]['date'],
                    'change_percent': change_percent,
                    'type': 'spike' if change_percent > 0 else 'drop'
                })

        return patterns

    def _get_instance_cpu_utilization(self, instance_id: str) -> Optional[float]:
        """EC2 인스턴스 CPU 사용률 조회 (시뮬레이션)"""
        # 실제 구현: CloudWatch에서 데이터 조회
        return 15.0  # 시뮬레이션 값

    def _get_downsized_instance_type(self, current_type: str) -> str:
        """다운사이징된 인스턴스 타입 제안"""
        downsize_map = {
            't3.2xlarge': 't3.xlarge',
            't3.xlarge': 't3.large',
            't3.large': 't3.medium',
            'm5.2xlarge': 'm5.xlarge',
            'm5.xlarge': 'm5.large',
        }
        return downsize_map.get(current_type, current_type)

    def _calculate_instance_savings(self, current_type: str, recommended_type: str) -> float:
        """인스턴스 다운사이징으로 예상되는 월간 절감액"""
        # t3.xlarge: $0.1664/hour, t3.large: $0.0832/hour
        hourly_savings = {
            ('t3.2xlarge', 't3.xlarge'): 0.1664,
            ('t3.xlarge', 't3.large'): 0.0832,
            ('t3.large', 't3.medium'): 0.0416,
            ('m5.2xlarge', 'm5.xlarge'): 0.192,
        }
        hourly_saving = hourly_savings.get((current_type, recommended_type), 50.0)
        return hourly_saving * 24 * 30  # 월간

    def _get_database_cpu_utilization(self, db_id: str) -> Optional[float]:
        """RDS 인스턴스 CPU 사용률 조회 (시뮬레이션)"""
        return 12.0  # 시뮬레이션 값

    def _get_database_memory_utilization(self, db_id: str) -> Optional[float]:
        """RDS 인스턴스 메모리 사용률 조회 (시뮬레이션)"""
        return 25.0  # 시뮬레이션 값

    def _get_database_monthly_cost(self, db_class: str) -> float:
        """RDS 인스턴스 월간 비용"""
        cost_map = {
            'db.t3.small': 100.0,
            'db.t3.medium': 150.0,
            'db.r5.large': 400.0,
            'db.r5.2xlarge': 1600.0,
            'db.r5.4xlarge': 3200.0,
        }
        return cost_map.get(db_class, 500.0)

    def _get_downsized_database_class(self, current_class: str) -> str:
        """다운사이징된 RDS 인스턴스 클래스 제안"""
        downsize_map = {
            'db.r5.4xlarge': 'db.r5.2xlarge',
            'db.r5.2xlarge': 'db.r5.xlarge',
            'db.r5.xlarge': 'db.t3.large',
        }
        return downsize_map.get(current_class, current_class)
