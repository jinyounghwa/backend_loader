"""
리소스 최적화 제안 엔진
미사용 리소스 식별, 오버프로비저닝 감지, Reserved Instance 추천
"""

from typing import Dict, List, Any
from datetime import datetime, timezone


class OptimizationSuggester:
    """비용 절감 최적화 제안"""

    def __init__(self):
        self.min_monthly_savings_threshold = 10  # $10 이상만 제안

    async def suggest_optimizations(
        self,
        findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        비용 절감 최적화 제안 생성

        Args:
            findings: 체크 결과 (EC2, S3, RDS 등)

        Returns:
            최적화 제안 리스트 (높은 절감액 순서)
        """
        suggestions = []

        # 1. 미사용 리소스 식별
        unused = await self._find_unused_resources(findings)
        suggestions.extend(unused)

        # 2. 오버프로비저닝 식별
        overprovisioned = await self._find_overprovisioned_resources(findings)
        suggestions.extend(overprovisioned)

        # 3. Reserved Instance 추천
        reserved_ops = await self._suggest_reserved_instances(findings)
        suggestions.extend(reserved_ops)

        # 4. 스케일 최적화
        scaling_ops = await self._suggest_scaling_optimizations(findings)
        suggestions.extend(scaling_ops)

        # 절감액 기준으로 정렬
        suggestions.sort(key=lambda x: x["potential_savings"], reverse=True)

        return suggestions

    async def _find_unused_resources(
        self,
        findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """미사용 리소스 식별"""
        suggestions = []

        # EC2 미사용 인스턴스 (CPU < 5%, 네트워크 < 100KB/h)
        if "ec2" in findings:
            for instance in findings.get("instances", []):
                if instance.get("cpu_utilization", 0) < 5:
                    monthly_cost = instance.get("monthly_cost", 0)
                    suggestions.append({
                        "type": "terminate_unused",
                        "resource_type": "EC2",
                        "resource_id": instance.get("instance_id"),
                        "reason": f"Low utilization: {instance.get('cpu_utilization', 0):.1f}% CPU",
                        "potential_savings": monthly_cost,
                        "priority": "high",
                        "action": f"Terminate instance {instance.get('instance_id')}",
                    })

        # S3 미사용 버킷 (0 개체, 0 요청)
        if "s3" in findings:
            for bucket in findings.get("buckets", []):
                if bucket.get("object_count", 0) == 0:
                    monthly_cost = bucket.get("monthly_cost", 0)
                    suggestions.append({
                        "type": "delete_empty_bucket",
                        "resource_type": "S3",
                        "resource_id": bucket.get("bucket_name"),
                        "reason": "Empty bucket with no objects",
                        "potential_savings": monthly_cost,
                        "priority": "low",
                        "action": f"Delete bucket {bucket.get('bucket_name')}",
                    })

        # RDS 미사용 DB (낮은 연결 수)
        if "rds" in findings:
            for db in findings.get("databases", []):
                if db.get("active_connections", 0) == 0:
                    monthly_cost = db.get("monthly_cost", 0)
                    suggestions.append({
                        "type": "terminate_unused_db",
                        "resource_type": "RDS",
                        "resource_id": db.get("db_identifier"),
                        "reason": "No active connections",
                        "potential_savings": monthly_cost,
                        "priority": "medium",
                        "action": f"Delete DB {db.get('db_identifier')} or create snapshot",
                    })

        return [s for s in suggestions if s["potential_savings"] >= self.min_monthly_savings_threshold]

    async def _find_overprovisioned_resources(
        self,
        findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """오버프로비저닝된 리소스 식별"""
        suggestions = []

        # EC2 오버프로비저닝 (큰 인스턴스, 낮은 사용률)
        if "ec2" in findings:
            for instance in findings.get("instances", []):
                cpu_util = instance.get("cpu_utilization", 0)
                memory_util = instance.get("memory_utilization", 0)

                if cpu_util < 20 and memory_util < 20:
                    current_cost = instance.get("monthly_cost", 0)
                    downsize_factor = 0.5  # 절반 크기로 축소

                    suggestions.append({
                        "type": "downsize_instance",
                        "resource_type": "EC2",
                        "resource_id": instance.get("instance_id"),
                        "current_type": instance.get("instance_type"),
                        "reason": f"Low utilization: CPU {cpu_util:.1f}%, Memory {memory_util:.1f}%",
                        "potential_savings": current_cost * (1 - downsize_factor),
                        "priority": "high",
                        "action": f"Downsize from {instance.get('instance_type')} to smaller type",
                    })

        return [s for s in suggestions if s["potential_savings"] >= self.min_monthly_savings_threshold]

    async def _suggest_reserved_instances(
        self,
        findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Reserved Instance 추천"""
        suggestions = []

        # EC2 RI 추천 (실행 중인 인스턴스 유형 집계)
        if "ec2" in findings:
            instance_types = {}
            for instance in findings.get("instances", []):
                itype = instance.get("instance_type")
                monthly_cost = instance.get("monthly_cost", 0)

                if itype not in instance_types:
                    instance_types[itype] = {"count": 0, "monthly_cost": 0}

                instance_types[itype]["count"] += 1
                instance_types[itype]["monthly_cost"] += monthly_cost

            # 충분한 인스턴스가 있는 유형만 RI 추천
            for itype, data in instance_types.items():
                if data["count"] >= 2:  # 최소 2개 이상
                    monthly_cost = data["monthly_cost"]
                    ri_savings = monthly_cost * 0.35  # RI로 35% 절감

                    suggestions.append({
                        "type": "purchase_reserved_instance",
                        "resource_type": "EC2",
                        "instance_type": itype,
                        "instance_count": data["count"],
                        "reason": f"Running {data['count']} {itype} instances continuously",
                        "potential_savings": ri_savings,
                        "priority": "high",
                        "action": f"Purchase 1-year RI for {data['count']} {itype} instances",
                    })

        return [s for s in suggestions if s["potential_savings"] >= self.min_monthly_savings_threshold]

    async def _suggest_scaling_optimizations(
        self,
        findings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """스케일 최적화 제안"""
        suggestions = []

        # Auto Scaling 그룹 추천
        if "ec2" in findings and len(findings.get("instances", [])) >= 5:
            total_cost = sum(i.get("monthly_cost", 0) for i in findings.get("instances", []))

            suggestions.append({
                "type": "enable_autoscaling",
                "resource_type": "EC2",
                "reason": "Multiple EC2 instances detected - enable Auto Scaling for cost optimization",
                "potential_savings": total_cost * 0.15,  # 15% 절감 예상
                "priority": "medium",
                "action": "Set up Auto Scaling Group with appropriate metrics",
            })

        # Spot Instances 추천
        if "ec2" in findings:
            on_demand_cost = sum(
                i.get("monthly_cost", 0)
                for i in findings.get("instances", [])
                if i.get("instance_type", "").startswith("t")  # T 시리즈는 덜 중요
            )

            if on_demand_cost > 100:  # $100 이상
                suggestions.append({
                    "type": "use_spot_instances",
                    "resource_type": "EC2",
                    "reason": "Suitable instances for Spot Instance usage",
                    "potential_savings": on_demand_cost * 0.70,  # 70% 절감
                    "priority": "medium",
                    "action": "Migrate eligible instances to Spot Instances",
                })

        return [s for s in suggestions if s.get("potential_savings", 0) >= self.min_monthly_savings_threshold]

    def get_summary(self, suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """최적화 요약"""
        if not suggestions:
            return {
                "total_potential_savings": 0,
                "count": 0,
                "by_priority": {"high": 0, "medium": 0, "low": 0},
            }

        total_savings = sum(s.get("potential_savings", 0) for s in suggestions)

        by_priority = {"high": 0, "medium": 0, "low": 0}
        for s in suggestions:
            priority = s.get("priority", "low")
            if priority in by_priority:
                by_priority[priority] += 1

        return {
            "total_potential_savings": round(total_savings, 2),
            "count": len(suggestions),
            "by_priority": by_priority,
            "monthly_savings": round(total_savings, 2),
            "annual_savings": round(total_savings * 12, 2),
        }


# 전역 제안 엔진
_suggester = OptimizationSuggester()


async def suggest_optimizations(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """최적화 제안 생성 (async)"""
    return await _suggester.suggest_optimizations(findings)


def suggest_optimizations_sync(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """최적화 제안 생성 (sync)"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(_suggester.suggest_optimizations(findings))
    loop.close()
    return result
