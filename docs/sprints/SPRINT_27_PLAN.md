# Sprint 27: 모바일 앱 & 고급 기능

**Status:** 📋 PLANNED  
**Target:** React Native 모바일 앱, PDF 보고서 생성, 자동 치료, 대규모 환경 지원

---

## Sprint 27 Overview

Sprint 26에서 구축한 웹 대시보드를 기반으로 모바일 앱을 개발하고, 고급 기능 추가:

1. **모바일 앱** - React Native (iOS/Android)
2. **보고서 생성** - PDF 및 CSV 내보내기
3. **자동 치료** - 위협 자동 격리 규칙
4. **대규모 환경** - 1000+ 리소스 지원

---

## 7.1: React Native 모바일 앱

### 앱 구조

```
apps/mobile/
├── app.json
├── App.tsx
├── screens/
│   ├── DashboardScreen.tsx
│   ├── EventsScreen.tsx
│   ├── ThreatScreen.tsx
│   └── SettingsScreen.tsx
├── components/
│   ├── StatusCard.tsx
│   ├── EventCard.tsx
│   └── ThreatIndicator.tsx
├── hooks/
│   └── useAPI.ts
└── lib/
    └── api.ts
```

### 핵심 기능

```tsx
// screens/DashboardScreen.tsx
export default function DashboardScreen() {
  const { status, loading } = useAPI('/api/guardian/status');
  
  return (
    <ScrollView>
      <StatusCard status={status.ec2} title="EC2" />
      <StatusCard status={status.s3} title="S3" />
      <StatusCard status={status.cost} title="Cost" />
      <ThreatIndicator score={status.threat_score} />
    </ScrollView>
  );
}
```

### 배포

```bash
# iOS
cd apps/mobile
npx react-native run-ios

# Android
npx react-native run-android

# 빌드
eas build --platform ios
eas build --platform android
```

---

## 7.2: 보고서 생성

### PDF 리포트

```tsx
// api/guardian/reports/pdf
export async function POST(request: NextRequest) {
  const { startDate, endDate } = await request.json();
  
  const events = await getEvents(startDate, endDate);
  const threats = await analyzeThreatTimeline(startDate, endDate);
  const actions = await getActions(startDate, endDate);
  
  const doc = new PDFDocument();
  doc.fontSize(20).text('AWS Guardian Report');
  doc.fontSize(12).text(`Period: ${startDate} to ${endDate}`);
  
  // Add charts, tables, etc.
  return doc.pipe(response);
}
```

### CSV 내보내기

```tsx
// api/guardian/reports/csv
export async function GET(request: NextRequest) {
  const { type } = request.nextUrl.searchParams;
  
  if (type === 'events') {
    const events = await getAllEvents();
    const csv = convertToCSV(events);
    return new Response(csv, { 
      headers: { 'Content-Type': 'text/csv' }
    });
  }
}
```

---

## 7.3: 자동 치료 (Auto-Remediation)

### 자동 격리 규칙

```python
# lambda/guardian/remediation/auto_remediation.py
class AutoRemediationEngine:
    async def apply_remediation(self, threat):
        """Automatically isolate or remediate threats"""
        
        if threat['type'] == 'public_bucket':
            # 자동: S3 퍼블릭 액세스 차단
            await self.block_public_s3(threat['resource_id'])
        
        elif threat['type'] == 'unauthorized_region':
            # 자동: EC2 인스턴스 중지
            await self.stop_ec2_instance(threat['resource_id'])
        
        elif threat['type'] == 'high_cost':
            # 수동 검토 필요
            await self.alert_admin(threat)
            
    async def block_public_s3(self, bucket_name):
        """S3 퍼블릭 액세스 차단"""
        s3 = await get_async_client('s3')
        await s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
```

### 자동 치료 API

```tsx
// api/guardian/remediation/auto
export async function POST(request: NextRequest) {
  const { threat_id, action } = await request.json();
  
  // action: 'block_s3', 'stop_ec2', 'require_approval'
  const result = await remediationEngine.execute(threat_id, action);
  
  return NextResponse.json({
    success: true,
    action_id: result.id,
    status: result.status,
    timestamp: new Date().toISOString()
  });
}
```

---

## 7.4: 대규모 환경 지원

### 병렬 처리 최적화

```python
# lambda/guardian/orchestrator_v2.py
class ScalableOrchestrator:
    async def check_all_regions_parallel(self):
        """모든 리전 동시 확인"""
        ec2_client = await get_async_client('ec2')
        
        # 모든 리전 병렬 조회
        regions = await self.get_all_regions(ec2_client)
        tasks = [
            self.check_region(region) 
            for region in regions
        ]
        
        results = await asyncio.gather(*tasks)
        return aggregate_results(results)
    
    async def paginate_resources(self, resource_type):
        """1000+ 리소스 처리"""
        client = await get_async_client('ec2')
        paginator = client.get_paginator('describe_instances')
        
        all_instances = []
        async for page in paginator.paginate():
            for reservation in page['Reservations']:
                all_instances.extend(reservation['Instances'])
        
        return all_instances
```

### 캐시 전략

```python
# 1시간 캐시 (변경 빈도 낮음)
@cache.cached(ttl=3600)
async def get_region_list():
    return await ec2_client.describe_regions()

# 5분 캐시 (변경 빈도 중간)
@cache.cached(ttl=300)
async def get_cost_data():
    return await cost_explorer.get_cost_and_usage()

# 캐시 없음 (실시간)
async def get_recent_events():
    return await dynamodb.query_recent_events()
```

---

## 7.5: 데이터베이스 최적화

### 인덱싱 및 파티셔닝

```sql
-- 빠른 조회를 위한 인덱스
CREATE INDEX idx_events_timestamp_severity 
  ON events(timestamp DESC, severity);

CREATE INDEX idx_events_resource_id 
  ON events(resource_id);

-- 시간 기반 파티셔닝 (검색 성능 향상)
ALTER TABLE events 
PARTITION BY RANGE (MONTH(timestamp)) (
    PARTITION p_jan VALUES LESS THAN (2),
    PARTITION p_feb VALUES LESS THAN (3),
    ...
    PARTITION p_dec VALUES LESS THAN (13)
);
```

### DynamoDB Global Secondary Index

```python
# events 테이블 GSI
{
  'IndexName': 'severity-timestamp-index',
  'KeySchema': [
    {'AttributeName': 'severity', 'KeyType': 'HASH'},
    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
  ],
  'Projection': {'ProjectionType': 'ALL'},
  'ProvisionedThroughput': {
    'ReadCapacityUnits': 100,
    'WriteCapacityUnits': 50
  }
}
```

---

## 7.6: 테스트

### E2E 테스트

```tsx
// __tests__/e2e/mobile.test.ts
describe('Mobile App', () => {
  it('loads dashboard and displays status', async () => {
    const screen = render(<DashboardScreen />);
    
    await waitFor(() => {
      expect(screen.getByText('AWS Guardian')).toBeInTheDocument();
    });
  });
});
```

### 보고서 테스트

```python
# tests/test_reports.py
def test_pdf_generation():
    response = client.post('/api/guardian/reports/pdf', {
        'startDate': '2026-05-01',
        'endDate': '2026-05-31'
    })
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
```

---

## 7.7: 배포

### 모바일 앱 배포

```bash
# Expo로 배포
npx eas submit --platform ios
npx eas submit --platform android

# 또는 직접 배포
# App Store Connect (iOS)
# Google Play Console (Android)
```

### 백엔드 업데이트

```bash
# 새로운 Lambda 함수 배포
sam deploy -t sam-remediation.yaml

# 환경 변수 업데이트
aws lambda update-function-configuration \
  --function-name guardianAutoRemediation \
  --environment Variables='{...}'
```

---

## 7.8: 성공 기준

✅ **모바일 앱**
- iOS/Android 모두 빌드 성공
- 대시보드 화면 로드 < 2초
- 오프라인 기본 데이터 캐싱
- 푸시 알림 작동

✅ **보고서**
- PDF 생성 < 5초 (1000+ 이벤트)
- CSV 내보내기 작동
- 이메일 자동 전송

✅ **자동 치료**
- S3 퍼블릭 접근 자동 차단
- EC2 비인가 리전 자동 중지
- 자동 치료 로그 기록

✅ **대규모 환경**
- 1000+ EC2 인스턴스 처리 < 30초
- 500+ S3 버킷 처리 < 20초
- 캐시 적중률 70%+

---

## 7.9: 타임라인

| 단계 | 예상 시간 | 필수 리소스 |
|------|----------|-----------|
| 모바일 앱 개발 | 120 min | React Native |
| 보고서 생성 | 60 min | pdfkit, csv |
| 자동 치료 | 90 min | Lambda |
| 대규모 환경 | 60 min | 최적화 |
| 테스트 | 45 min | Jest, pytest |
| 배포 | 30 min | Expo, SAM |
| **Total** | **405 min** | - |

---

## 7.10: 다음 단계 (Sprint 28)

- 머신러닝 모델 고도화 (scikit-learn)
- 실시간 이상 탐지 개선
- GraphQL API 추가
- 멀티 클라우드 지원 (Azure, GCP)
- 성능 튜닝 (lambda concurrency)

---

**Sprint 27 준비 완료!** 🚀
