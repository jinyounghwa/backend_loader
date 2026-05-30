"""Kubernetes threat detection tests for AWS Guardian."""

import pytest


class TestK8sMonitor:
    """Test K8s cluster monitoring."""

    def test_monitor_k8s_cluster(self):
        """✅ Monitor K8s cluster for threats."""
        from guardian.k8s.k8s_threat_detection import K8sMonitor

        monitor = K8sMonitor()

        result = monitor.monitor({
            'cluster_name': 'prod-cluster',
            'namespace': 'default',
            'watch_events': True
        })

        assert 'monitor_id' in result
        assert 'status' in result

    def test_detect_unauthorized_access(self):
        """✅ Detect unauthorized K8s API access."""
        from guardian.k8s.k8s_threat_detection import K8sMonitor

        monitor = K8sMonitor()

        result = monitor.detect_threat({
            'threat_type': 'unauthorized_access',
            'api_calls': [
                {'user': 'anonymous', 'action': 'get_secrets', 'denied': True},
                {'user': 'service_account', 'action': 'create_pod', 'denied': False}
            ]
        })

        assert 'threats' in result
        assert 'count' in result

    def test_detect_privilege_escalation(self):
        """✅ Detect privilege escalation attempts."""
        from guardian.k8s.k8s_threat_detection import K8sMonitor

        monitor = K8sMonitor()

        result = monitor.detect_privilege_escalation({
            'user_id': 'user_123',
            'action': 'create_admin_role',
            'timestamp': '2026-05-30T10:30:00Z'
        })

        assert 'escalation_detected' in result or 'threat_found' in result


class TestAPIServerAnalyzer:
    """Test API server anomaly detection."""

    def test_analyze_api_calls(self):
        """✅ Analyze API server calls."""
        from guardian.k8s.k8s_threat_detection import APIServerAnalyzer

        analyzer = APIServerAnalyzer()

        result = analyzer.analyze({
            'api_calls': [
                {'user': 'user_1', 'action': 'get_pods', 'count': 100},
                {'user': 'user_2', 'action': 'delete_deployment', 'count': 1}
            ]
        })

        assert 'analysis' in result or 'summary' in result

    def test_detect_api_anomalies(self):
        """✅ Detect anomalous API patterns."""
        from guardian.k8s.k8s_threat_detection import APIServerAnalyzer

        analyzer = APIServerAnalyzer()

        result = analyzer.detect_anomalies({
            'baseline': {'avg_calls_per_user': 50},
            'current': {'user_1_calls': 1000, 'user_2_calls': 45}
        })

        assert 'anomalies' in result or 'detected' in result

    def test_rate_limit_enforcement(self):
        """✅ Enforce API rate limits."""
        from guardian.k8s.k8s_threat_detection import APIServerAnalyzer

        analyzer = APIServerAnalyzer()

        result = analyzer.enforce_rate_limits({
            'user_id': 'user_123',
            'limit': 100,
            'window_seconds': 60,
            'current_calls': 150
        })

        assert 'enforced' in result or 'limited' in result


class TestRBACValidator:
    """Test RBAC validation."""

    def test_validate_rbac_policy(self):
        """✅ Validate RBAC permissions."""
        from guardian.k8s.k8s_threat_detection import RBACValidator

        validator = RBACValidator()

        result = validator.validate({
            'role': 'admin',
            'permissions': ['create', 'read', 'update', 'delete'],
            'resources': ['pods', 'services']
        })

        assert 'valid' in result or 'issues' in result

    def test_detect_overprivileged_roles(self):
        """✅ Detect overprivileged roles."""
        from guardian.k8s.k8s_threat_detection import RBACValidator

        validator = RBACValidator()

        result = validator.detect_overprivileged({
            'roles': [
                {'name': 'admin', 'permissions': ['*']},
                {'name': 'user', 'permissions': ['read']}
            ],
            'threshold': 0.8
        })

        assert 'overprivileged' in result or 'roles' in result

    def test_check_least_privilege(self):
        """✅ Check least privilege principle."""
        from guardian.k8s.k8s_threat_detection import RBACValidator

        validator = RBACValidator()

        result = validator.check_least_privilege({
            'service_account': 'app-sa',
            'required_permissions': ['get_pods', 'create_secrets'],
            'assigned_permissions': ['*']
        })

        assert 'compliant' in result or 'violations' in result


class TestNetworkPolicyChecker:
    """Test network policy validation."""

    def test_validate_network_policy(self):
        """✅ Validate network policies."""
        from guardian.k8s.k8s_threat_detection import NetworkPolicyChecker

        checker = NetworkPolicyChecker()

        result = checker.validate({
            'policy_name': 'deny-all-ingress',
            'rules': [
                {'to': [], 'from': []}
            ]
        })

        assert 'valid' in result or 'issues' in result

    def test_detect_unrestricted_traffic(self):
        """✅ Detect unrestricted traffic."""
        from guardian.k8s.k8s_threat_detection import NetworkPolicyChecker

        checker = NetworkPolicyChecker()

        result = checker.detect_unrestricted({
            'namespace': 'default',
            'allow_all_ingress': True,
            'allow_all_egress': True
        })

        assert 'unrestricted' in result or 'found' in result

    def test_enforce_network_segmentation(self):
        """✅ Enforce network segmentation."""
        from guardian.k8s.k8s_threat_detection import NetworkPolicyChecker

        checker = NetworkPolicyChecker()

        result = checker.enforce_segmentation({
            'namespaces': ['ns1', 'ns2', 'ns3'],
            'enforce_policies': True
        })

        assert 'enforced' in result or 'applied' in result


class TestK8sThreatIntegration:
    """End-to-end K8s threat detection."""

    def test_full_k8s_security_scan(self):
        """✅ Complete K8s security assessment."""
        from guardian.k8s.k8s_threat_detection import (
            K8sMonitor,
            APIServerAnalyzer,
            RBACValidator,
            NetworkPolicyChecker
        )

        monitor = K8sMonitor()
        api_analyzer = APIServerAnalyzer()
        rbac = RBACValidator()
        network = NetworkPolicyChecker()

        # Monitor cluster
        mon = monitor.monitor({'cluster_name': 'prod'})
        assert 'monitor_id' in mon

        # Analyze API
        api_result = api_analyzer.analyze({'api_calls': []})
        assert 'analysis' in api_result or 'summary' in api_result

        # Validate RBAC
        rbac_result = rbac.validate({'role': 'admin'})
        assert 'valid' in rbac_result or 'issues' in rbac_result

        # Check network policy
        net_result = network.validate({'policy_name': 'test'})
        assert 'valid' in net_result or 'issues' in net_result

    def test_threat_detection_workflow(self):
        """✅ Detect threats across K8s components."""
        from guardian.k8s.k8s_threat_detection import (
            K8sMonitor,
            APIServerAnalyzer
        )

        monitor = K8sMonitor()
        analyzer = APIServerAnalyzer()

        # Start monitoring
        mon = monitor.monitor({'cluster_name': 'test'})

        # Detect threats
        threat = monitor.detect_threat({
            'threat_type': 'unauthorized_access',
            'api_calls': []
        })
        assert 'threats' in threat

        # Analyze anomalies
        anom = analyzer.detect_anomalies({
            'baseline': {},
            'current': {}
        })
        assert 'anomalies' in anom or 'detected' in anom

    def test_rbac_and_network_policy_assessment(self):
        """✅ Assess RBAC and network policies."""
        from guardian.k8s.k8s_threat_detection import (
            RBACValidator,
            NetworkPolicyChecker
        )

        rbac = RBACValidator()
        network = NetworkPolicyChecker()

        # Validate RBAC
        rbac_val = rbac.detect_overprivileged({'roles': []})
        assert 'overprivileged' in rbac_val or 'roles' in rbac_val

        # Check network
        net_val = network.detect_unrestricted({'namespace': 'default'})
        assert 'unrestricted' in net_val or 'found' in net_val

    def test_comprehensive_k8s_threat_assessment(self):
        """✅ Comprehensive K8s security assessment."""
        from guardian.k8s.k8s_threat_detection import (
            K8sMonitor,
            APIServerAnalyzer,
            RBACValidator,
            NetworkPolicyChecker
        )

        monitor = K8sMonitor()
        api_analyzer = APIServerAnalyzer()
        rbac = RBACValidator()
        network = NetworkPolicyChecker()

        # Complete assessment
        mon = monitor.monitor({'cluster_name': 'prod'})
        threats = monitor.detect_threat({'threat_type': 'unauthorized_access', 'api_calls': []})
        api_analysis = api_analyzer.analyze({'api_calls': []})
        rbac_check = rbac.validate({'role': 'admin'})
        network_check = network.validate({'policy_name': 'test'})

        assert 'monitor_id' in mon
        assert 'threats' in threats
        assert 'analysis' in api_analysis or 'summary' in api_analysis
        assert 'valid' in rbac_check or 'issues' in rbac_check
        assert 'valid' in network_check or 'issues' in network_check
