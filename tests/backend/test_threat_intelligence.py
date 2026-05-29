import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from guardian.intelligence.threat_intelligence import ThreatIntelligence
from guardian.intelligence.cve_checker import CVEChecker
from guardian.intelligence.ip_reputation import IPReputation


class TestCVEChecker:
    """CVE Checker 테스트"""

    @pytest.fixture
    def mock_nvd(self):
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        cache = Mock()
        cache.get = Mock(return_value=None)
        cache.setex = Mock()
        return cache

    @pytest.fixture
    def cve_checker(self, mock_nvd, mock_cache):
        return CVEChecker(mock_nvd, mock_cache)

    @pytest.mark.asyncio
    async def test_find_matching_cves_apache(self, cve_checker):
        """CVE 조회 - Apache 예시"""
        cves = await cve_checker.find_matching_cves('Apache', '2.4.41')

        assert len(cves) == 1
        assert cves[0]['cve_id'] == 'CVE-2021-41773'
        assert cves[0]['severity'] == 'CRITICAL'
        assert cves[0]['cvss_score'] == 10.0

    @pytest.mark.asyncio
    async def test_cve_cache_hit(self, cve_checker, mock_cache):
        """CVE 캐시 저장/재사용"""
        cached_cve = [
            {
                'cve_id': 'CVE-2021-41773',
                'severity': 'CRITICAL',
                'cvss_score': 10.0,
                'description': 'Test CVE',
                'published_date': '2021-10-05',
                'attack_vector': 'NETWORK'
            }
        ]

        # 캐시 설정
        mock_cache.get = Mock(return_value=json.dumps(cached_cve))

        cves = await cve_checker.find_matching_cves('Apache', '2.4.41')

        # 캐시에서 조회했는지 확인
        mock_cache.get.assert_called()
        assert len(cves) == 1

    @pytest.mark.asyncio
    async def test_cve_vulnerability_trend(self, cve_checker):
        """소프트웨어 취약점 추세 분석"""
        trend = await cve_checker.check_software_vulnerability_trend('Apache')

        assert 'total_cves' in trend
        assert 'critical_count' in trend
        assert 'trend' in trend

    @pytest.mark.asyncio
    async def test_is_cve_critical(self, cve_checker):
        """CVE 심각도 판단"""
        critical_cve = {'severity': 'CRITICAL', 'cvss_score': 10.0}
        high_cve = {'severity': 'HIGH', 'cvss_score': 7.5}

        assert cve_checker.is_cve_critical(critical_cve) is True
        assert cve_checker.is_cve_critical(high_cve) is False

    @pytest.mark.asyncio
    async def test_get_cve_details_url(self, cve_checker):
        """CVE 상세 정보 URL 생성"""
        url = cve_checker.get_cve_details_url('CVE-2021-41773')

        assert 'CVE-2021-41773' in url
        assert 'nvd.nist.gov' in url


class TestIPReputation:
    """IP 평판 조회 테스트"""

    @pytest.fixture
    def mock_api(self):
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        cache = Mock()
        cache.get = Mock(return_value=None)
        cache.setex = Mock()
        return cache

    @pytest.fixture
    def ip_reputation(self, mock_api, mock_cache):
        return IPReputation(mock_api, mock_cache)

    @pytest.mark.asyncio
    async def test_check_reputation_malicious_ip(self, ip_reputation):
        """악성 IP 조회"""
        result = await ip_reputation.check_reputation('123.45.67.89')

        assert result['is_malicious'] is True
        assert result['abuse_score'] == 85
        assert 'Proxy/VPN' in result['threat_types']

    @pytest.mark.asyncio
    async def test_check_reputation_clean_ip(self, ip_reputation):
        """정상 IP 조회"""
        result = await ip_reputation.check_reputation('1.1.1.1')

        assert result['is_malicious'] is False
        assert result['abuse_score'] == 0

    @pytest.mark.asyncio
    async def test_ip_reputation_cache(self, ip_reputation, mock_cache):
        """IP 평판 캐시"""
        cached_result = {
            'ip': '123.45.67.89',
            'is_malicious': True,
            'abuse_score': 85,
            'threat_types': ['Proxy/VPN'],
            'last_reported': '2024-05-25T10:30:00Z',
            'total_reports': 145,
            'country': 'CN'
        }

        mock_cache.get = Mock(return_value=json.dumps(cached_result))

        result = await ip_reputation.check_reputation('123.45.67.89')

        assert result['is_malicious'] is True
        mock_cache.get.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_ip_address(self, ip_reputation):
        """유효하지 않은 IP 처리"""
        result = await ip_reputation.check_reputation('invalid.ip.address')

        assert result['is_malicious'] is False
        assert result['abuse_score'] == 0

    @pytest.mark.asyncio
    async def test_private_ip_address(self, ip_reputation):
        """사설 IP 처리"""
        result = await ip_reputation.check_reputation('192.168.1.1')

        # 사설 IP는 악성으로 표시되지 않음
        assert result['is_malicious'] is False

    @pytest.mark.asyncio
    async def test_get_threat_level_from_score(self, ip_reputation):
        """점수 → 위협도 변환"""
        assert ip_reputation.get_threat_level_from_score(95) == 'CRITICAL'
        assert ip_reputation.get_threat_level_from_score(75) == 'HIGH'
        assert ip_reputation.get_threat_level_from_score(50) == 'MEDIUM'
        assert ip_reputation.get_threat_level_from_score(25) == 'LOW'
        assert ip_reputation.get_threat_level_from_score(10) == 'MINIMAL'


class TestThreatIntelligence:
    """ThreatIntelligence 통합 테스트"""

    @pytest.fixture
    def mock_cve_db(self):
        return Mock()

    @pytest.fixture
    def mock_ip_api(self):
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        cache = Mock()
        cache.get = Mock(return_value=None)
        cache.setex = Mock()
        return cache

    @pytest.fixture
    def threat_intelligence(self, mock_cve_db, mock_ip_api, mock_cache):
        return ThreatIntelligence(mock_cve_db, mock_ip_api, mock_cache)

    @pytest.mark.asyncio
    async def test_enrich_threat_with_cve(self, threat_intelligence):
        """위협 + CVE 데이터 → 보강됨"""
        threat = {
            'threat_id': 'threat_1',
            'threat_type': 'software_vulnerability',
            'severity': 'MEDIUM',
            'software': 'Apache',
            'version': '2.4.41',
            'source_ip': '8.8.8.8',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        enriched = await threat_intelligence.enrich_threat(threat)

        assert enriched['threat_level_adjusted'] == 'CRITICAL'  # CVE 발견으로 상향
        assert len(enriched['cve_matches']) > 0
        assert enriched['confidence_score'] >= 1.0

    @pytest.mark.asyncio
    async def test_enrich_threat_with_ip_rep(self, threat_intelligence):
        """위협 + IP 평판 → 보강됨"""
        threat = {
            'threat_id': 'threat_2',
            'threat_type': 'suspicious_connection',
            'severity': 'LOW',
            'source_ip': '123.45.67.89',  # 악성 IP
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        enriched = await threat_intelligence.enrich_threat(threat)

        assert enriched['threat_level_adjusted'] == 'CRITICAL'  # IP 평판으로 상향
        assert len(enriched['malicious_ips']) > 0
        assert enriched['confidence_score'] >= 1.0

    @pytest.mark.asyncio
    async def test_batch_enrich_parallel(self, threat_intelligence):
        """여러 위협 동시 보강 → 병렬 처리"""
        threats = [
            {
                'threat_id': f'threat_{i}',
                'threat_type': 'connection_spike',
                'severity': 'MEDIUM',
                'software': 'Apache',
                'version': '2.4.41',
                'source_ip': '8.8.8.8',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }
            for i in range(3)
        ]

        enriched_threats = await threat_intelligence.batch_enrich(threats)

        assert len(enriched_threats) == 3
        for enriched in enriched_threats:
            assert 'original_threat' in enriched
            assert 'enrichment_status' in enriched
            assert enriched['original_threat'].get('threat_id') is not None

    @pytest.mark.asyncio
    async def test_threat_score_adjustments(self, threat_intelligence):
        """보강된 위협 정보로부터 점수 조정"""
        enriched_threat = {
            'original_threat': {},
            'cve_matches': [
                {'cve_id': 'CVE-1', 'cvss_score': 9.0},
                {'cve_id': 'CVE-2', 'cvss_score': 8.5}
            ],
            'malicious_ips': [
                {'ip': '123.45.67.89', 'abuse_score': 85}
            ],
            'threat_level_adjusted': 'CRITICAL',
            'confidence_score': 1.5
        }

        adjustments = threat_intelligence.get_threat_score_adjustments(enriched_threat)

        assert adjustments['cve_score_adjustment'] > 0
        assert adjustments['ip_reputation_adjustment'] > 0
        assert adjustments['total_adjustment'] > 0

    @pytest.mark.asyncio
    async def test_enrich_threat_no_extra_info(self, threat_intelligence):
        """추가 정보 없이 위협 보강"""
        threat = {
            'threat_id': 'threat_3',
            'threat_type': 'unknown_region',
            'severity': 'HIGH',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        enriched = await threat_intelligence.enrich_threat(threat)

        # 원본 심각도 유지
        assert enriched['threat_level_adjusted'] == 'HIGH'
        assert len(enriched['cve_matches']) == 0
        assert len(enriched['malicious_ips']) == 0
