# Sprint 14 계획: Gemini AI 위협 분석 + 성능 최적화

**상태**: 📋 Plan Phase  
**시작**: 2026-05-04 (다음 세션)  
**예상 기간**: 2.5시간 (150분)  
**우선순위**: Phase 1 (필수) > Phase 2 (선택)

---

## 🎯 Phase 1: Gemini AI 실시간 위협 분석 (90분) - PRIORITY

### 목표
CloudTrail/GuardDuty 이벤트를 Gemini API로 실시간 분석하여 AI 기반 위협 평가(Critical/High/Medium) 및 자동 대응 권고 제공.

### 기술 스택
- **Gemini API SDK**: `@google/generative-ai`
- **패턴**: Streaming API (interactive) vs one-shot (경제적)
- **인증**: NextAuth 보안 (API 엔드포인트)
- **토큰 캐싱**: 비용 절감 (CloudTrail 패턴 반복)

### 구현 계획

#### 1.1 `/api/analyze-threat` 엔드포인트
**파일**: `apps/web/src/app/api/analyze-threat/route.ts`

```ts
import { auth } from '@auth';
import { GoogleGenerativeAI } from '@google/generative-ai';

export async function POST(request: Request) {
  const session = await auth();
  if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });

  const { events } = await request.json();

  const client = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
  const model = client.getGenerativeModel({ model: 'gemini-2.0-flash' });

  const prompt = `Analyze these AWS security events and provide:
1. Threat severity (Critical/High/Medium/Low)
2. Root cause analysis
3. Immediate remediation steps
4. Prevention recommendations

Events: ${JSON.stringify(events)}`;

  try {
    const result = await model.generateContent(prompt);
    const analysis = result.response.text();
    return Response.json({ analysis, severity: 'High' });
  } catch (error) {
    return Response.json({ error: 'Analysis failed' }, { status: 500 });
  }
}
```

#### 1.2 `useAIAnalysis` 훅
**파일**: `apps/web/src/lib/hooks/useAIAnalysis.ts`

- CloudTrail 이벤트 수집
- Debounced 요청 (5초)
- 캐시 관리 (같은 이벤트 패턴)
- 에러 처리

#### 1.3 `AIThreatPanel` 컴포넌트
**파일**: `apps/web/src/components/Dashboard/AIThreatPanel.tsx`

```tsx
// AI 위협 분석 결과 표시
// - Severity badge (Critical/High/Medium)
// - Root cause
// - Remediation steps
// - Prevention tips
```

**위치**: RiskScore 옆에 배치 (grid col-span-2)

#### 1.4 RiskScore 통합
`RiskScore.tsx` 수정:
- AI 심각도 점수 표시
- Gemini 분석 타임스탬프
- "Refresh Analysis" 버튼

### 환경 설정

**.env.local** 추가:
```bash
GOOGLE_API_KEY=your-gemini-api-key
GOOGLE_PROJECT_ID=your-project-id
```

**package.json** 추가:
```json
{
  "dependencies": {
    "@google/generative-ai": "^0.7.0"
  }
}
```

### 기술 결정사항

#### Streaming vs One-shot
- ✅ **One-shot** 추천 (비용 절감 + 구현 간단)
- ❌ Streaming: 더 interactive하나 토큰 비용 높음

#### 토큰 캐싱
- ✅ **사용**: CloudTrail 스키마 반복 (30% 비용 절감)
- 예: "Analyze AWS CloudTrail events: {events}"

#### API 할당량 관리
- Rate limit: 요청당 1-2초 delay
- Batch 분석: 최대 10 이벤트/요청
- Fallback: 캐시된 이전 분석 결과

### 예상 이슈 & 해결책

| 이슈 | 해결책 |
|------|--------|
| API 비용 (월 $0.075/1M tokens) | 토큰 캐싱 + Batch 요청 |
| 토큰 제한 (일일 할당량) | Queuing 시스템 구현 |
| 응답 지연 (2-3초) | 낙관적 UI 업데이트 |
| 모델 한계 (기술적 분석만) | 정책 기반 규칙 추가 |

---

## 🎯 Phase 2: 성능 최적화 & Lighthouse (60분) - OPTIONAL

### 목표
Lighthouse 점수 80+ 달성, 번들 크기 최적화, Core Web Vitals 개선.

### 성능 지표

| 메트릭 | 현재 | 목표 |
|--------|------|------|
| Lighthouse | 70-75 | 80+ |
| Bundle Size | 1.8MB | 1.5MB |
| LCP | <3.5s | <2.5s |
| FID | <100ms | <50ms |
| CLS | <0.1 | <0.05 |

### 최적화 항목

#### 2.1 번들 크기 감소
- Recharts 트리 셰이킹 (사용 안 하는 차트 제거)
- Dynamic import for heavy components
- Image optimization (WebP + responsive)

#### 2.2 LCP 개선
- Critical CSS 분리
- Preload key resources
- Font loading 최적화

#### 2.3 메모리 프로파일링
- React DevTools Profiler
- Unnecessary re-renders 제거
- Context 분할 (너무 큰 공급자)

#### 2.4 캐싱 전략
- Static asset 캐싱 (1년)
- API response 캐싱 (5분)
- Service Worker 업데이트 (60초)

### 구현 순서

1. Lighthouse audit (`npm run build && npx lighthouse`)
2. Chrome DevTools Performance tab
3. Memory profiler (heap snapshots)
4. 핵심 3가지 최적화 먼저
5. 재측정 및 반복

---

## 📊 파일 변경 예상

### Phase 1
```
NEW FILES:
✨ src/app/api/analyze-threat/route.ts (60 LOC)
✨ src/lib/hooks/useAIAnalysis.ts (50 LOC)
✨ src/components/Dashboard/AIThreatPanel.tsx (80 LOC)

MODIFIED:
📝 src/components/Dashboard/RiskScore.tsx (AI 결과 통합)
📝 src/app/page.tsx (AIThreatPanel 추가)
```

### Phase 2
```
MODIFIED:
📝 next.config.js (image optimization)
📝 tsconfig.json (module resolution)
📝 src/components/Dashboard/ (tree-shake)
```

---

## 🔗 Gemini 협업 워크플로우

### Phase 1 Gemini 검토 포인트
1. ✅ Streaming vs one-shot 확인
2. ✅ 토큰 캐싱 전략 검증
3. ✅ 에러 처리 및 fallback
4. ✅ API 할당량 관리

### Phase 2 (선택사항)
- Performance audit 결과 해석
- 최적화 우선순위 결정

---

## 📋 시작 체크리스트 (다음 세션)

```
Session Start Checklist:
-----------------------
[ ] Gemini API 키 설정 (.env.local)
[ ] `@google/generative-ai` 설치
[ ] SPRINT_14_PLAN.md 읽음
[ ] npm run dev 실행 (zero errors)
[ ] 현재 Lighthouse 점수 측정 (baseline)

Optional:
--------
[ ] Gemini API 비용 추정
[ ] CloudTrail 샘플 이벤트 준비
[ ] RiskScore 디자인 확인 (AI 결과 표시 위치)
```

---

## 🚀 향후 로드맵

| Sprint | 기능 | 상태 |
|--------|------|------|
| Sprint 13 | Mobile + Notifications + Offline | ✅ DONE |
| Sprint 14 | Gemini AI + Performance | 🔮 Planning |
| Sprint 15 | Multi-region deployment | 🔮 Planned |
| Sprint 16 | Advanced Analytics | 🔮 Planned |

---

**Gemini 협업**: Plan → Review → Implement → CodeReview → Document  
**Next**: Gemini API 검토 후 Phase 1 구현 시작

