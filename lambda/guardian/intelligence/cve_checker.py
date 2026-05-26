import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class CVEChecker:
    """CVE 데이터베이스 조회 및 캐싱"""

    def __init__(self, nvd_client, cache):
        """
        Args:
            nvd_client: NVD REST API 클라이언트
            cache: 캐시 저장소 (Redis 등)
        """
        self.nvd = nvd_client
        self.cache = cache
        self.cache_ttl = 7 * 24 * 3600  # 7일

    async def find_matching_cves(self, software: str, version: str) -> List[Dict[str, Any]]:
        """
        소프트웨어 → 해당 CVE 목록 조회

        Args:
            software: 소프트웨어명 (e.g., 'Apache', 'OpenSSL')
            version: 버전 (e.g., '2.4.41')

        Returns:
            [
                {
                    'cve_id': 'CVE-2024-12345',
                    'severity': 'CRITICAL',
                    'cvss_score': 9.8,
                    'description': '...',
                    'published_date': '2024-01-01',
                    'attack_vector': 'NETWORK'
                },
                ...
            ]
        """
        # 캐시 키 생성
        cache_key = f"cve:{software.lower()}:{version}"

        # 1. 캐시 확인
        cached = await self._get_cache(cache_key)
        if cached is not None:
            logger.debug(f"CVE cache hit for {software} v{version}")
            return cached

        # 2. NVD API 조회
        cves = await self._query_nvd(software, version)

        # 3. 캐시 저장
        if cves:
            await self._set_cache(cache_key, cves, self.cache_ttl)
            logger.info(f"Cached {len(cves)} CVEs for {software} v{version}")

        return cves

    async def _query_nvd(self, software: str, version: str) -> List[Dict[str, Any]]:
        """
        NVD REST API 호출

        Note: 실제 구현에서는 NVD API를 호출합니다.
        현재는 모의 구현입니다.
        """
        try:
            # 실제 API 호출 로직 (여기서는 모의)
            # response = await self.nvd.get_vulnerabilities(
            #     keyword=f"{software} {version}",
            #     limit=20
            # )

            cves = []
            # 모의 데이터 반환
            if software.lower() == 'apache' and version == '2.4.41':
                cves = [
                    {
                        'cve_id': 'CVE-2021-41773',
                        'severity': 'CRITICAL',
                        'cvss_score': 10.0,
                        'description': 'Apache HTTP Server 2.4.41 through 2.4.49 allows...',
                        'published_date': '2021-10-05',
                        'attack_vector': 'NETWORK'
                    }
                ]
            elif software.lower() == 'openssl':
                cves = [
                    {
                        'cve_id': 'CVE-2023-4807',
                        'severity': 'HIGH',
                        'cvss_score': 7.5,
                        'description': 'OpenSSL vulnerability in key derivation...',
                        'published_date': '2023-09-19',
                        'attack_vector': 'NETWORK'
                    }
                ]

            logger.debug(f"NVD query returned {len(cves)} CVEs for {software} v{version}")
            return cves

        except Exception as e:
            logger.error(f"NVD API query failed: {e}")
            return []

    async def _get_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """캐시에서 조회"""
        try:
            if not self.cache:
                return None

            cached_data = self.cache.get(cache_key)
            if cached_data:
                if isinstance(cached_data, str):
                    return json.loads(cached_data)
                return cached_data
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    async def _set_cache(self, cache_key: str, data: List[Dict[str, Any]], ttl: int) -> None:
        """캐시에 저장"""
        try:
            if not self.cache:
                return

            self.cache.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    async def check_software_vulnerability_trend(self, software: str) -> Dict[str, Any]:
        """
        소프트웨어의 취약점 추세 분석

        Returns:
            {
                'total_cves': int,
                'critical_count': int,
                'high_count': int,
                'recent_cves': List[str],
                'trend': 'increasing' | 'stable' | 'decreasing'
            }
        """
        # 향후 구현: NVD 통계 API 활용
        return {
            'total_cves': 0,
            'critical_count': 0,
            'high_count': 0,
            'recent_cves': [],
            'trend': 'stable'
        }

    def is_cve_critical(self, cve: Dict[str, Any]) -> bool:
        """CVE의 심각도 판단"""
        severity = cve.get('severity', '').upper()
        cvss_score = cve.get('cvss_score', 0)

        return severity == 'CRITICAL' or cvss_score >= 9.0

    def get_cve_details_url(self, cve_id: str) -> str:
        """CVE 상세 정보 URL"""
        return f"https://nvd.nist.gov/vuln/detail/{cve_id}"
