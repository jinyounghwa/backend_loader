"""Custom exception classes for AWS Guardian system"""


class GuardianException(Exception):
    """기본 Guardian 예외 클래스"""
    pass


class TicketingException(GuardianException):
    """티켓팅 서비스 관련 예외"""
    pass


class WorkflowExecutionException(GuardianException):
    """워크플로우 실행 예외"""
    pass


class SOARIntegrationException(GuardianException):
    """SOAR 플랫폼 통합 예외"""
    pass


class ValidationException(GuardianException):
    """데이터 검증 실패 예외"""
    pass


class RetryableException(GuardianException):
    """재시도 가능한 예외 (네트워크 오류 등)"""
    pass


class ServiceUnavailableException(GuardianException):
    """서비스 이용 불가 예외"""
    pass


class ConfigurationException(GuardianException):
    """설정 오류 예외"""
    pass
