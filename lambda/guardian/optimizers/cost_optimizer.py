"""Predictive cost optimization: Instance sizing, RI recommendations, Spot strategy"""

from typing import Dict, List


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
