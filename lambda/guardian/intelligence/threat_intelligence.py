import asyncio
import logging
from typing import Dict, List, Any, Optional
from guardian.intelligence.cve_checker import CVEChecker
from guardian.intelligence.ip_reputation import IPReputation

logger = logging.getLogger(__name__)


class ThreatIntelligence:
    """외부 위협 정보(CVE, IP 평판)를 활용한 위협 탐지 강화"""

    def __init__(self, cve_db, ip_reputation_api, cache):
        """
        Args:
            cve_db: CVE 데이터베이스 클라이언트
            ip_reputation_api: IP 평판 API 클라이언트
            cache: 캐시 저장소 (Redis 등)
        """
        self.cve = CVEChecker(cve_db, cache)
        self.ip_rep = IPReputation(ip_reputation_api, cache)

    async def enrich_threat(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """
        탐지된 위협에 외부 정보 추가

        Args:
            threat: {
                'threat_id': str,
                'threat_type': str,
                'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'software': str (선택),
                'version': str (선택),
                'source_ip': str (선택),
                'timestamp': str
            }

        Returns:
            {
                'original_threat': {...},
                'cve_matches': [...],
                'malicious_ips': [...],
                'threat_level_adjusted': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'confidence_score': float (0.0-1.0),
                'enrichment_status': 'success' | 'partial' | 'failed'
            }
        """
        enriched = {
            'original_threat': threat,
            'cve_matches': [],
            'malicious_ips': [],
            'threat_level_adjusted': threat.get('severity', 'MEDIUM'),
            'confidence_score': 1.0,
            'enrichment_status': 'success'
        }

        errors = []

        try:
            # 1. CVE 확인 (병렬 처리)
            if threat.get('software') and threat.get('version'):
                try:
                    cves = await self.cve.find_matching_cves(
                        threat.get('software'),
                        threat.get('version')
                    )
                    enriched['cve_matches'] = cves

                    if cves:
                        # CVE 발견 시 위협도 상향
                        enriched['threat_level_adjusted'] = 'CRITICAL'
                        # 신뢰도 증가 (CVE당 +20%)
                        enriched['confidence_score'] = min(1.0, 1.0 + 0.2 * min(len(cves), 3))

                        logger.info(f"Found {len(cves)} CVEs for {threat.get('software')} v{threat.get('version')}")
                except Exception as e:
                    logger.warning(f"CVE check failed: {e}")
                    errors.append(f"CVE check error: {e}")

            # 2. IP 평판 확인
            if threat.get('source_ip'):
                try:
                    ip_rep = await self.ip_rep.check_reputation(threat.get('source_ip'))

                    if ip_rep['is_malicious']:
                        enriched['malicious_ips'].append(ip_rep)

                        # 악성 IP 발견 시 위협도 상향
                        enriched['threat_level_adjusted'] = 'CRITICAL'
                        # 신뢰도 증가 (+30%)
                        enriched['confidence_score'] = min(1.0, enriched['confidence_score'] + 0.3)

                        logger.info(f"Found malicious IP: {threat.get('source_ip')} (score: {ip_rep['abuse_score']})")
                except Exception as e:
                    logger.warning(f"IP reputation check failed: {e}")
                    errors.append(f"IP check error: {e}")

            # 보강 상태 결정
            if errors:
                enriched['enrichment_status'] = 'partial' if enriched['cve_matches'] or enriched['malicious_ips'] else 'failed'

        except Exception as e:
            logger.error(f"Failed to enrich threat {threat.get('threat_id')}: {e}")
            enriched['enrichment_status'] = 'failed'
            enriched['confidence_score'] = 0.5

        return enriched

    async def batch_enrich(self, threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        여러 위협 동시 보강 (병렬 처리)

        Args:
            threats: 위협 목록

        Returns:
            보강된 위협 목록
        """
        if not threats:
            return []

        tasks = [self.enrich_threat(threat) for threat in threats]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_threats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to enrich threat {i}: {result}")
                # 원본 위협 반환 (보강 없이)
                enriched_threats.append({
                    'original_threat': threats[i],
                    'cve_matches': [],
                    'malicious_ips': [],
                    'threat_level_adjusted': threats[i].get('severity', 'MEDIUM'),
                    'confidence_score': 0.5,
                    'enrichment_status': 'failed'
                })
            else:
                enriched_threats.append(result)

        logger.info(f"Batch enriched {len(enriched_threats)} threats")
        return enriched_threats

    async def get_threat_context(self, threat_id: str) -> Dict[str, Any]:
        """
        위협 ID로 전체 컨텍스트 조회

        Returns:
            {
                'threat_id': str,
                'threat_type': str,
                'related_cves': List[str],
                'related_malicious_actors': List[str],
                'recommended_actions': List[str]
            }
        """
        # 향후 위협 인텔리전스 DB에서 추가 정보 조회
        return {
            'threat_id': threat_id,
            'related_cves': [],
            'related_malicious_actors': [],
            'recommended_actions': []
        }

    def get_threat_score_adjustments(self, enriched_threat: Dict[str, Any]) -> Dict[str, float]:
        """
        보강된 위협 정보로부터 점수 조정 계산

        Returns:
            {
                'cve_score_adjustment': float,
                'ip_reputation_adjustment': float,
                'total_adjustment': float
            }
        """
        cve_adjustment = 0.0
        ip_adjustment = 0.0

        if enriched_threat['cve_matches']:
            # CVE당 +10%점
            cve_adjustment = min(0.3, 0.1 * len(enriched_threat['cve_matches']))

        if enriched_threat['malicious_ips']:
            # IP 평판 점수 활용
            avg_abuse_score = sum(ip['abuse_score'] for ip in enriched_threat['malicious_ips']) / len(enriched_threat['malicious_ips'])
            ip_adjustment = (avg_abuse_score / 100) * 0.3  # 최대 +30%

        return {
            'cve_score_adjustment': round(cve_adjustment, 3),
            'ip_reputation_adjustment': round(ip_adjustment, 3),
            'total_adjustment': round(cve_adjustment + ip_adjustment, 3)
        }
