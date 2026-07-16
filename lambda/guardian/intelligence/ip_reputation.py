import logging
import json
import ipaddress
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IPReputation:
    """IP 주소 평판 조회 (AbuseIPDB)"""

    def __init__(self, abuseipdb_client, cache):
        """
        Args:
            abuseipdb_client: AbuseIPDB API 클라이언트
            cache: 캐시 저장소 (Redis 등)
        """
        self.api = abuseipdb_client
        self.cache = cache
        self.cache_ttl = 24 * 3600  # 24시간

    async def check_reputation(self, ip_address: str) -> Dict[str, Any]:
        """
        IP 평판 조회 (AbuseIPDB)

        Args:
            ip_address: IP 주소

        Returns:
            {
                'ip': str,
                'is_malicious': bool,
                'abuse_score': int (0-100),
                'threat_types': List[str],
                'last_reported': str (ISO format),
                'total_reports': int,
                'country': str
            }
        """
        # IP 유효성 검증
        if not self._is_valid_ip(ip_address):
            logger.warning(f"Invalid IP address: {ip_address}")
            return {
                'ip': ip_address,
                'is_malicious': False,
                'abuse_score': 0,
                'threat_types': [],
                'last_reported': None,
                'total_reports': 0,
                'country': 'UNKNOWN'
            }

        # 캐시 확인 (24시간)
        cache_key = f"ip_rep:{ip_address}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            logger.debug(f"IP reputation cache hit: {ip_address}")
            return cached

        # AbuseIPDB API 호출
        result = await self._query_abuseipdb(ip_address)

        # 캐시 저장
        if result:
            await self._set_cache(cache_key, result, self.cache_ttl)

        return result

    async def _query_abuseipdb(self, ip_address: str) -> Dict[str, Any]:
        """
        AbuseIPDB API 호출

        Note: 실제 구현에서는 AbuseIPDB API를 호출합니다.
        현재는 모의 구현입니다.
        """
        try:
            # 실제 API 호출 로직 (여기서는 모의)
            # response = await self.api.check(
            #     ipAddress=ip_address,
            #     maxAgeInDays=90,
            #     verbose=True
            # )

            # 모의 데이터 반환
            result = {
                'ip': ip_address,
                'is_malicious': False,
                'abuse_score': 0,
                'threat_types': [],
                'last_reported': None,
                'total_reports': 0,
                'country': 'UNKNOWN'
            }

            # 악성 IP 예시
            if ip_address == '123.45.67.89':
                result = {
                    'ip': ip_address,
                    'is_malicious': True,
                    'abuse_score': 85,
                    'threat_types': ['Proxy/VPN', 'Brute Force'],
                    'last_reported': '2024-05-25T10:30:00Z',
                    'total_reports': 145,
                    'country': 'CN'
                }
            elif self._is_private_ip(ip_address):
                result['is_malicious'] = False
                result['threat_types'] = []

            logger.debug(f"AbuseIPDB query returned score {result['abuse_score']} for {ip_address}")
            return result

        except Exception as e:
            logger.error(f"AbuseIPDB API query failed: {e}")
            return {
                'ip': ip_address,
                'is_malicious': False,
                'abuse_score': 0,
                'threat_types': [],
                'last_reported': None,
                'total_reports': 0,
                'country': 'UNKNOWN'
            }

    async def check_batch_reputation(self, ip_addresses: list) -> Dict[str, Dict[str, Any]]:
        """
        여러 IP의 평판 동시 조회

        Args:
            ip_addresses: IP 주소 목록

        Returns:
            {
                'ip_1': {...},
                'ip_2': {...},
                ...
            }
        """
        import asyncio

        results = {}
        tasks = [self.check_reputation(ip) for ip in ip_addresses]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for ip, response in zip(ip_addresses, responses):
            if isinstance(response, Exception):
                logger.error(f"Failed to check IP {ip}: {response}")
                results[ip] = {
                    'ip': ip,
                    'is_malicious': False,
                    'abuse_score': 0,
                    'threat_types': [],
                    'last_reported': None,
                    'total_reports': 0,
                    'country': 'UNKNOWN'
                }
            else:
                results[ip] = response

        return results

    async def _get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
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

    async def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int) -> None:
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

    def _is_valid_ip(self, ip_address: str) -> bool:
        """IP 주소 유효성 검증 (stdlib ipaddress 기반, IPv4/IPv6 정확 파싱)."""
        if not isinstance(ip_address, str):
            return False
        try:
            ipaddress.ip_address(ip_address.strip())
            return True
        except ValueError:
            return False

    def _is_private_ip(self, ip_address: str) -> bool:
        """사설/예약 IP 판단.

        stdlib 를 사용해 RFC1918 사설 대역뿐 아니라 루프백, 링크로컬
        (169.254.0.0/16 — 클라우드 메타데이터 169.254.169.254 포함),
        예약/미지정(0.0.0.0) 대역까지 모두 내부로 분류한다. 이 값들은
        외부 평판 조회 대상이 아니며 안전한 것으로 취급되어서는 안 된다.
        """
        try:
            ip = ipaddress.ip_address(ip_address.strip())
        except ValueError:
            return False
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or ip.is_multicast
        )

    def get_threat_level_from_score(self, abuse_score: int) -> str:
        """AbuseIPDB 점수 → 위협도 변환"""
        if abuse_score >= 90:
            return 'CRITICAL'
        elif abuse_score >= 75:
            return 'HIGH'
        elif abuse_score >= 50:
            return 'MEDIUM'
        elif abuse_score >= 25:
            return 'LOW'
        else:
            return 'MINIMAL'
