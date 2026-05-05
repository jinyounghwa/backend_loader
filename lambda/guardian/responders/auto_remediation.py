"""Auto-remediation actions for AWS Guardian Telegram commands"""

import logging
from datetime import datetime, timezone as tz
from typing import List, Dict, Any

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider
from guardian.responders.aws_action_executor import AWSActionExecutor

logger = logging.getLogger("auto_remediation")

MAX_INSTANCES_STOP_LIMIT = 5
PROTECTED_TAG_KEY = "GuardianProtected"
SKIP_TAG_KEY = "AutoManaged"
SKIP_TAG_VALUE = "false"


def remediate_cost_overrun() -> dict:
    results = {
        "action": "요금과다 원인수정",
        "timestamp": datetime.now(tz.utc).isoformat(),
        "steps": [],
        "summary": "",
    }

    try:
        if Config.is_localstack():
            results["steps"].append(
                {
                    "name": "비용 상세 분석",
                    "detail": "LocalStack: 일일 $5.50 / 월간 $150.50 (mock)",
                    "status": "analyzed",
                }
            )
            results["steps"].append(
                {
                    "name": "상위 비용 서비스 식별",
                    "detail": "LocalStack: EC2(t2.micro x3)가 주요 비용 원인으로 추정",
                    "status": "identified",
                }
            )
            results["steps"].append(
                {
                    "name": "비용 임계값 유지 (수동 확인 필요)",
                    "detail": "자동 임계값 상향은 위험하므로 분석 결과만 제공",
                    "status": "done",
                }
            )

            results["summary"] = (
                "비용 원인 분석 완료.\n"
                "- 주요 원인: EC2 인스턴스 다수 실행\n"
                "- ⚠️ 임계값 자동 상향은 보안상 비활성화됨\n"
                "- /threshold 명령으로 수동 조정 가능"
            )
        else:
            ce = AWSClientProvider.get_client("ce")
            today = datetime.now(tz.utc).strftime("%Y-%m-%d")
            yesterday = (datetime.now(tz.utc).replace(hour=0, minute=0, second=0)).strftime(
                "%Y-%m-%d"
            )

            top_services: List[str] = []
            try:
                response = ce.get_cost_and_usage(
                    TimePeriod={"Start": yesterday, "End": today},
                    Granularity="DAILY",
                    Metrics=["UnblendedCost"],
                    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                )

                if response.get("ResultsByTime"):
                    groups = response["ResultsByTime"][0].get("Groups", [])
                    for g in sorted(
                        groups,
                        key=lambda x: float(x["Metrics"]["UnblendedCost"]["Amount"]),
                        reverse=True,
                    )[:3]:
                        top_services.append(
                            f"{g['Keys'][0]}: ${float(g['Metrics']['UnblendedCost']['Amount']):.2f}"
                        )

                results["steps"].append(
                    {
                        "name": "비용 상세 분석",
                        "detail": "\n".join(top_services) if top_services else "No data",
                        "status": "analyzed",
                    }
                )
            except Exception as ce_error:
                logger.warning("Cost Explorer API failed: %s", ce_error)
                results["steps"].append(
                    {
                        "name": "비용 상세 분석",
                        "detail": "Cost Explorer API 조회 실패 (권한 확인)",
                        "status": "failed",
                    }
                )

            results["steps"].append(
                {
                    "name": "임계값 자동 상향 안함 (보안)",
                    "detail": "비용 이상을 숨길 수 있으므로 수동 확인 필요: /threshold {amount}",
                    "status": "done",
                }
            )

            results["summary"] = (
                "비용 원인 분석 완료.\n"
                + (
                    "- 상위 서비스:\n" + "\n".join(f"  {s}" for s in top_services) + "\n"
                    if top_services
                    else ""
                )
                + "- ⚠️ 임계값 자동 상향은 보안상 비활성화됨\n"
                "- /threshold {금액} 으로 수동 조정"
            )

    except Exception as e:
        logger.error("Cost remediation error: %s", e)
        results["steps"].append(
            {"name": "자동 수정", "detail": f"오류: {str(e)}", "status": "failed"}
        )
        results["summary"] = f"자동 수정 실패: {str(e)}"

    return results


def _is_protected_instance(instance: Dict[str, Any]) -> bool:
    tags = instance.get("Tags", [])
    for tag in tags:
        if tag.get("Key") == PROTECTED_TAG_KEY:
            return True
        if tag.get("Key") == SKIP_TAG_KEY and tag.get("Value", "").lower() == SKIP_TAG_VALUE:
            return True
    return False


def _get_all_regions() -> list:
    ec2 = AWSClientProvider.get_client("ec2")
    response = ec2.describe_regions()
    return [r["RegionName"] for r in response["Regions"]]


def remediate_hacking_suspicion() -> dict:
    results = {
        "action": "해킹우려 수정",
        "timestamp": datetime.now(tz.utc).isoformat(),
        "steps": [],
        "summary": "",
    }

    try:
        stopped_instances: List[str] = []
        skipped_instances: List[str] = []
        blocked_buckets: List[str] = []

        regions = ["us-east-1"] if Config.is_localstack() else _get_all_regions()
        executor = AWSActionExecutor()

        for region in regions:
            ec2 = AWSClientProvider.get_client("ec2", region=region)

            try:
                response = ec2.describe_instances(
                    Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                )

                stoppable_ids: List[str] = []
                for reservation in response.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        instance_id = instance["InstanceId"]
                        if _is_protected_instance(instance):
                            skipped_instances.append(f"{instance_id} ({region})")
                            logger.info(
                                "Skipping protected instance: %s in %s", instance_id, region
                            )
                            continue
                        stoppable_ids.append(instance_id)

                if stoppable_ids:
                    if len(stoppable_ids) > MAX_INSTANCES_STOP_LIMIT:
                        results["steps"].append(
                            {
                                "name": f"EC2 중지 ({region})",
                                "detail": (
                                    f"⚠️ 중지 대상 {len(stoppable_ids)}개 > 안전 한계 {MAX_INSTANCES_STOP_LIMIT}개. "
                                    f"수동 확인 필요: /stop {{instance-id}}"
                                ),
                                "status": "failed",
                            }
                        )
                        logger.warning(
                            "Too many stoppable instances (%d) in %s, exceeding safety limit %d",
                            len(stoppable_ids),
                            region,
                            MAX_INSTANCES_STOP_LIMIT,
                        )
                        continue

                    for iid in stoppable_ids:
                        success = executor.stop_ec2_instance(iid, region)
                        if success:
                            stopped_instances.append(f"{iid} ({region})")
                        else:
                            results["steps"].append(
                                {
                                    "name": f"EC2 중지 실패 ({region})",
                                    "detail": f"인스턴스 {iid} 중지 실패",
                                    "status": "failed",
                                }
                            )
            except Exception as e:
                logger.error("Failed to stop instances in %s: %s", region, e)
                results["steps"].append(
                    {"name": f"EC2 중지 ({region})", "detail": str(e), "status": "failed"}
                )

        if stopped_instances:
            results["steps"].append(
                {
                    "name": "EC2 인스턴스 중지",
                    "detail": f"{len(stopped_instances)}개 인스턴스 중지: "
                    + ", ".join(stopped_instances[:5]),
                    "status": "done",
                }
            )

        if skipped_instances:
            results["steps"].append(
                {
                    "name": "보호된 인스턴스 (스킵)",
                    "detail": f"{len(skipped_instances)}개 스킵: "
                    + ", ".join(skipped_instances[:5]),
                    "status": "done",
                }
            )

        s3 = AWSClientProvider.get_client("s3")

        try:
            buckets_response = s3.list_buckets()
            for bucket in buckets_response.get("Buckets", []):
                bucket_name = bucket["Name"]
                success = executor.block_s3_public_access(bucket_name)
                if success:
                    blocked_buckets.append(bucket_name)
                else:
                    logger.warning("Failed to block public access for %s", bucket_name)

            if blocked_buckets:
                results["steps"].append(
                    {
                        "name": "S3 퍼블릭 액세스 차단",
                        "detail": f"{len(blocked_buckets)}개 버킷 차단: "
                        + ", ".join(blocked_buckets[:5]),
                        "status": "done",
                    }
                )
        except Exception as s3_error:
            logger.error("S3 list buckets failed: %s", s3_error)
            results["steps"].append(
                {"name": "S3 퍼블릭 액세스 차단", "detail": str(s3_error), "status": "failed"}
            )

        summary_parts = [
            f"EC2: {len(stopped_instances)}개 중지",
            f"S3: {len(blocked_buckets)}개 퍼블릭 차단",
        ]
        if skipped_instances:
            summary_parts.append(f"⚠️ {len(skipped_instances)}개 보호됨 (스킵)")
        summary_parts.append("Security Group 0.0.0.0/0 규칙은 실 AWS에서 수동 확인 필요")

        results["summary"] = "보안 위협 자동 수정 완료.\n- " + "\n- ".join(summary_parts)

    except Exception as e:
        logger.error("Hacking suspicion remediation error: %s", e)
        results["steps"].append(
            {"name": "자동 수정", "detail": f"오류: {str(e)}", "status": "failed"}
        )
        results["summary"] = f"자동 수정 실패: {str(e)}"

    return results
