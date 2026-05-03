"""Gemini-powered threat analysis for AWS Guardian events"""
import json
import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class GeminiThreatAnalyzer:
    """Analyze AWS threats using Google Gemini AI"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini analyzer with caching"""
        if genai is None:
            raise ImportError("google-generativeai not installed")

        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self._cache = {}

    def analyze_threats(self, events_summary: Dict[str, Any]) -> str:
        """Analyze threat patterns and generate recommendations (with caching)"""
        # Generate cache key from events summary
        cache_key = self._generate_cache_key(events_summary)

        if cache_key in self._cache:
            logger.info("Using cached threat analysis")
            return self._cache[cache_key]

        try:
            prompt = self._build_prompt(events_summary)
            response = self.model.generate_content(prompt)
            analysis = response.text

            # Cache result for 1 hour
            self._cache[cache_key] = analysis
            return analysis

        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return self._generate_fallback_analysis(events_summary)

    def _generate_cache_key(self, events_summary: Dict[str, Any]) -> str:
        """Generate MD5 hash of events summary for caching"""
        summary_json = json.dumps(events_summary, sort_keys=True, default=str)
        return hashlib.md5(summary_json.encode()).hexdigest()

    def _build_prompt(self, events_summary: Dict[str, Any]) -> str:
        """Build Gemini prompt with Persona + Output Schema (Gemini recommended)"""
        return f"""[System Role]
당신은 AWS 환경의 Senior Cloud Security Architect입니다.
주어진 위협 데이터를 분석하고 실행 가능한 권장사항을 제시합니다.
응답은 Markdown 형식으로 명확하게 구조화하고, 한글로 작성합니다.

[Threat Data]
{json.dumps(events_summary, indent=2, ensure_ascii=False)}

[Output Schema]
다음 형식으로 정확히 응답:

# 분석 결과 (2026-{datetime.now(timezone.utc).strftime('%m-%d %H:%M UTC')})

## 🔍 주요 위협 패턴 (상위 3-5가지)
- [패턴]: [설명] (영향: [영향도])

## 🚨 우선순위별 대응 조치
### 🔴 긴급 (즉시 실행)
- [조치 1]: /stop 인스턴스 또는 차단
### 🟠 권장 (1시간 내)
- [조치 2]: 정책 변경 또는 감사
### 🟡 모니터링
- [조치 3]: 추가 모니터링 필요

## 🔐 추가 보안 강화
- [항목 1]: [상세 설명]

## 📊 다음 단계
/remediate {{finding-id}}로 자동 대응 실행 가능"""

    def _generate_fallback_analysis(self, events_summary: Dict[str, Any]) -> str:
        """Fallback analysis when Gemini API fails (basic statistics)"""
        total = events_summary.get("total_events", 0)
        severity = events_summary.get("by_severity", {})
        critical_count = severity.get("CRITICAL", 0)
        high_count = severity.get("HIGH", 0)

        return f"""# 위협 분석 (자동 생성 - Gemini 불가)

## 📊 요약
- **총 이벤트**: {total}개
- **심각도 분포**: 🔴 {critical_count} 🟠 {high_count} 🟡 {severity.get('MEDIUM', 0)}
- **이벤트 타입**: {', '.join(k for k in events_summary.get('by_type', {}).keys())}

## ⚠️ 즉시 조치 필요
{critical_count}개의 심각한 위협이 감지되었습니다.
/remediate {{finding-id}}로 자동 대응을 실행하세요.

*참고: Gemini API 접근 불가로 기본 통계만 제공됩니다.*"""
