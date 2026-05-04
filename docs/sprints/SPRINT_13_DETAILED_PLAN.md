# Sprint 13 상세 계획: 모바일 + 푸시 알림 + 오프라인 지원

**상태**: 🔵 Plan Phase  
**시작**: 2026-05-04  
**예상 기간**: 2.5시간 (3 phases, 150분)  
**Gemini 협업**: Plan → Review → Implement → CodeReview → Document

---

## 📋 Phase 1: 모바일 반응형 UI (45분)

### 목표
Tailwind CSS responsive breakpoints (md:, lg:)를 사용하여 모바일부터 데스크톱까지 최적화된 UI 구현.

### 기술 스택
- **Framework**: Tailwind CSS v4 (responsive classes)
- **Breakpoints**: mobile (0px) → tablet (768px: md:) → desktop (1024px: lg:)
- **Touch**: 최소 44×44px 클릭 영역
- **Viewport**: `viewport={{ width: 'device-width', initialScale: 1 }}`

### 구현 계획

#### 1.1 Dashboard Grid 레이아웃 조정
**파일**: `apps/web/src/app/page.tsx`

```
Mobile (1 col):
┌─────────────┐
│ AccountSel. │
├─────────────┤
│ RiskScore   │
├─────────────┤
│ EventFeed   │
├─────────────┤
│ ActionHist. │
└─────────────┘

Tablet (2 col md:):
┌────────────┬────────────┐
│ AccountSel │ RiskScore  │
├────────────┴────────────┤
│ EventFeed              │
├────────────────────────┤
│ ActionHistory         │
└────────────────────────┘

Desktop (3-4 col lg:):
┌─────────┬─────────┬─────────┐
│Account. │ Risk    │ other   │
├─────────┴─────────┴─────────┤
│ EventFeed  │  ActionHist.  │
└────────────┴───────────────┘
```

**변경사항**:
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` 적용
- gap 조정 (8px → 12px on tablet, 16px on desktop)
- 컴포넌트 크기 조정 (padding, text size)

#### 1.2 네비게이션 모바일 헤더
**파일**: `apps/web/src/components/layout/Header.tsx`

추가 기능:
- 모바일 hamburger 메뉴 (icon only)
- 드롭다운 메뉴 (session user, sign out)
- 헤더 높이: mobile 56px → tablet 64px
- 로고 크기: 24px → 32px (lg:)

```tsx
<header className="h-14 md:h-16 bg-slate-900 border-b">
  {/* Mobile: hamburger + logo only */}
  <div className="md:hidden flex items-center justify-between">
    <Menu className="w-5 h-5" />
  </div>
  
  {/* Desktop: full header */}
  <div className="hidden md:flex items-center justify-between">
    {/* full navigation */}
  </div>
</header>
```

#### 1.3 터치 친화적 버튼
**변경사항**:
- 최소 높이 44px (iOS guidance)
- 패딩: 12px → 16px (vertical)
- 간격: 8px → 12px (button group)

```tsx
<button className="px-3 md:px-4 py-3 md:py-2 min-h-[44px] md:min-h-auto">
```

#### 1.4 컴포넌트별 반응형 조정

| Component | Mobile | Tablet | Desktop |
|-----------|--------|--------|---------|
| AccountSelector | dropdown full-width | dropdown 200px | dropdown 250px |
| RiskScore | text-2xl | text-3xl | text-4xl |
| EventFeed | h-48 | h-64 | h-80 |
| ActionHistory | overflow-x-scroll | overflow-x-scroll | overflow-x-auto |
| AuditLogViewer | font-xs, truncate | font-sm | font-sm |

### 검증 기준
- [ ] Lighthouse Mobile 점수 > 80
- [ ] 터치 버튼 최소 44×44px
- [ ] 모바일/태블릿/데스크톱 시각적 일관성
- [ ] 콘솔 에러 0개

---

## 📋 Phase 2: 브라우저 푸시 알림 (60분)

### 목표
Web Notifications API를 사용하여 브라우저 푸시 알림 구현. 사용자 권한 요청 → 실시간 알림 표시.

### 기술 스택
- **API**: Web Notifications API (Notification, ServiceWorkerContainer)
- **Hook**: `useNotification` (React)
- **Provider**: `NotificationProvider` (React Context)
- **Endpoint**: `/api/notifications` (server-sent events)
- **권한**: 사용자 동의 필수

### 구현 계획

#### 2.1 `useNotification` 훅
**파일**: `apps/web/src/lib/hooks/useNotification.ts`

```tsx
export interface NotificationOptions {
  title: string;
  options?: NotificationOptions;
}

export function useNotification() {
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [isSupported] = useState(() => 'Notification' in window);

  const requestPermission = async () => {
    if (!isSupported) return false;
    const result = await Notification.requestPermission();
    setPermission(result);
    return result === 'granted';
  };

  const sendNotification = (title: string, options?: any) => {
    if (permission !== 'granted') return;
    if (Notification.permission === 'granted') {
      new Notification(title, options);
    }
  };

  return { permission, requestPermission, sendNotification, isSupported };
}
```

#### 2.2 `NotificationProvider` 컨텍스트
**파일**: `apps/web/src/components/NotificationProvider.tsx`

```tsx
export interface NotificationContextType {
  notify: (title: string, options?: any) => void;
  requestPermission: () => Promise<boolean>;
  permission: NotificationPermission;
}

export const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { permission, requestPermission, sendNotification } = useNotification();

  const notify = useCallback((title: string, options?: any) => {
    sendNotification(title, {
      icon: '/icon.png',
      badge: '/badge.png',
      tag: options?.tag || 'default',
      requireInteraction: options?.requireInteraction || false,
      ...options,
    });
  }, []);

  return (
    <NotificationContext.Provider value={{ notify, requestPermission, permission }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotificationContext() {
  const context = useContext(NotificationContext);
  if (!context) throw new Error('useNotificationContext outside provider');
  return context;
}
```

#### 2.3 권한 요청 모달
**파일**: `apps/web/src/components/NotificationPermissionModal.tsx`

```tsx
interface Props {
  isOpen: boolean;
  onAllow: () => Promise<void>;
  onDeny: () => void;
}

export function NotificationPermissionModal({ isOpen, onAllow, onDeny }: Props) {
  const [isLoading, setIsLoading] = useState(false);

  const handleAllow = async () => {
    setIsLoading(true);
    await onAllow();
    setIsLoading(false);
  };

  if (!isOpen) return null;

  return (
    <ConfirmationDialog
      isOpen={isOpen}
      title="알림 권한 요청"
      message="실시간 보안 알림을 받으시겠습니까?"
      confirmText="허용"
      cancelText="나중에"
      isLoading={isLoading}
      onConfirm={handleAllow}
      onCancel={onDeny}
    />
  );
}
```

#### 2.4 `/api/notifications` 엔드포인트
**파일**: `apps/web/src/app/api/notifications/route.ts`

```ts
// Server-Sent Events로 mock 알림 스트림
export async function GET(request: NextRequest) {
  const encoder = new TextEncoder();
  const customReadable = new ReadableStream({
    async start(controller) {
      // 30초마다 mock 알림 전송
      const interval = setInterval(() => {
        const events = [
          { title: 'Security Alert', body: 'Unauthorized access attempt detected' },
          { title: 'Cost Warning', body: 'Daily spend exceeded $15' },
          { title: 'S3 Alert', body: 'Public bucket detected: my-bucket' },
        ];
        const event = events[Math.floor(Math.random() * events.length)];
        
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
        );
      }, 30000);

      // 클라이언트 연결 종료 시 interval 정리
      request.signal.addEventListener('abort', () => {
        clearInterval(interval);
        controller.close();
      });
    },
  });

  return new Response(customReadable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

#### 2.5 ActionHistory 통합
**변경사항**: `apps/web/src/components/Dashboard/ActionHistory.tsx`

```tsx
const { notify } = useNotificationContext();

// remediate 성공 시
notify('액션 실행 성공', {
  body: `${action.action_type} on ${action.resource_id}`,
  tag: 'remediate',
  requireInteraction: true,
});
```

#### 2.6 초기 권한 요청
**변경사항**: `apps/web/src/app/layout.tsx`

```tsx
function NotificationPrompt() {
  const { permission, requestPermission } = useNotificationContext();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (permission === 'default') {
      setShowModal(true);
    }
  }, []);

  return (
    <NotificationPermissionModal
      isOpen={showModal}
      onAllow={requestPermission}
      onDeny={() => setShowModal(false)}
    />
  );
}
```

### HTTPS/LOCALHOST 주의
- ✅ Localhost에서는 HTTPS 불필요 (개발 가능)
- ❌ Production에서는 HTTPS 필수
- 보안: Service Worker는 HTTPS 환경에서만 등록 가능

### 검증 기준
- [ ] 권한 요청 모달 표시 및 승인/거부 가능
- [ ] 알림 권한 granted 시 실제 알림 전송
- [ ] EventSource 30초마다 mock 알림 수신
- [ ] 콘솔 에러 0개

---

## 📋 Phase 3: 오프라인 지원 (45분)

### 목표
Service Worker를 사용하여 네트워크 감지, 오프라인 캐싱, 재연결 시 캐시 무효화 구현.

### 기술 스택
- **API**: Service Worker, Cache API, IndexedDB (선택사항)
- **Hook**: `useOnline()` (네트워크 상태 감지)
- **Component**: `OfflineBanner` (상태 표시)
- **Strategy**: Cache-first (static assets) → Network-first (API calls)

### 구현 계획

#### 3.1 Service Worker 등록
**파일**: `apps/web/public/sw.js`

```javascript
const CACHE_NAME = 'guardian-v1';
const API_CACHE = 'guardian-api-v1';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/favicon.ico',
  // CSS/JS bundles
];

// Install: 정적 자산 캐싱
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: 오래된 캐시 삭제
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.map((name) => {
          if (name !== CACHE_NAME && name !== API_CACHE) {
            return caches.delete(name);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch: Cache-first (static) / Network-first (API)
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API 요청: Network-first
  if (url.pathname.startsWith('/api/')) {
    return event.respondWith(
      fetch(request)
        .then((response) => {
          // 성공하면 캐시 업데이트
          const clone = response.clone();
          caches.open(API_CACHE).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => {
          // 네트워크 실패 시 캐시 반환
          return caches.match(request);
        })
    );
  }

  // 정적 자산: Cache-first
  return event.respondWith(
    caches.match(request).then((response) => {
      return response || fetch(request);
    })
  );
});
```

#### 3.2 Service Worker 등록 스크립트
**파일**: `apps/web/src/app/layout.tsx` (useEffect 추가)

```tsx
useEffect(() => {
  if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
    navigator.serviceWorker
      .register('/sw.js')
      .then((reg) => console.log('SW registered:', reg))
      .catch((err) => console.error('SW registration failed:', err));
  }
}, []);
```

#### 3.3 `useOnline()` 훅
**파일**: `apps/web/src/lib/hooks/useOnline.ts`

```tsx
export function useOnline() {
  const [isOnline, setIsOnline] = useState(() => {
    // 초기 상태: navigator.onLine
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  });

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}
```

#### 3.4 `OfflineBanner` 컴포넌트
**파일**: `apps/web/src/components/OfflineBanner.tsx`

```tsx
import { WifiOff, Wifi } from 'lucide-react';
import { useOnline } from '@/lib/hooks/useOnline';

export function OfflineBanner() {
  const isOnline = useOnline();

  if (isOnline) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 bg-red-900/80 text-white px-4 py-3 flex items-center gap-2">
      <WifiOff className="w-4 h-4" />
      <span className="text-sm">오프라인 상태입니다. 캐시된 데이터를 사용하고 있습니다.</span>
    </div>
  );
}
```

#### 3.5 Providers 통합
**변경사항**: `apps/web/src/components/Providers.tsx`

```tsx
import { OfflineBanner } from './OfflineBanner';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ToastProvider>
        <NotificationProvider>
          <AccountProvider>
            {children}
            <OfflineBanner />
          </AccountProvider>
        </NotificationProvider>
      </ToastProvider>
    </SessionProvider>
  );
}
```

#### 3.6 캐시 무효화 전략
**변경사항**: `apps/web/src/app/page.tsx`

```tsx
useEffect(() => {
  const handleOnline = async () => {
    // 네트워크 복구 시 캐시 무효화
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames.map((name) => {
          if (name.includes('api')) {
            return caches.delete(name);
          }
        })
      );
    }
    // 데이터 재로드
    loadActions();
  };

  window.addEventListener('online', handleOnline);
  return () => window.removeEventListener('online', handleOnline);
}, []);
```

### 주의사항
- ⚠️ Service Worker는 **production build**에서만 활성화
- ⚠️ `navigator.onLine`은 오프라인 감지만 (정확도 100% 아님)
- ⚠️ Cache API 크기 제한 (일반적 50MB)
- ⚠️ IndexedDB 사용 시 추가 고려 (복잡도 증가)

### 검증 기준
- [ ] Service Worker 등록 (DevTools → Application → Service Workers)
- [ ] 오프라인 상태에서 정적 자산 로드 가능
- [ ] 오프라인 배너 표시/숨김 정상
- [ ] 네트워크 복구 시 캐시 무효화 및 재로드
- [ ] 콘솔 에러 0개

---

## 📊 파일 변경 요약

### NEW FILES
```
✨ apps/web/src/lib/hooks/useNotification.ts (45 LOC)
✨ apps/web/src/lib/hooks/useOnline.ts (25 LOC)
✨ apps/web/src/components/NotificationProvider.tsx (60 LOC)
✨ apps/web/src/components/NotificationPermissionModal.tsx (50 LOC)
✨ apps/web/src/components/OfflineBanner.tsx (25 LOC)
✨ apps/web/src/app/api/notifications/route.ts (50 LOC)
✨ apps/web/public/sw.js (100 LOC)
```

### MODIFIED FILES
```
📝 apps/web/src/app/page.tsx (responsive grid + offline handler)
📝 apps/web/src/app/layout.tsx (SW registration + NotificationPrompt)
📝 apps/web/src/components/Providers.tsx (NotificationProvider wrap)
📝 apps/web/src/components/layout/Header.tsx (mobile hamburger menu)
📝 apps/web/src/components/Dashboard/ActionHistory.tsx (notify integration)
```

---

## ⏱️ 시간 배분

```
Phase 1 (Mobile Responsive): 45분
  - Grid layout: 15분
  - Header/navigation: 15분
  - Component responsiveness: 15분

Phase 2 (Push Notifications): 60분
  - useNotification hook: 20분
  - NotificationProvider: 20분
  - /api/notifications: 10분
  - Integration: 10분

Phase 3 (Offline Support): 45분
  - Service Worker: 20분
  - useOnline hook + OfflineBanner: 15분
  - Cache strategy + integration: 10분

Total: 150분 (2.5시간)
```

---

## 🔗 Gemini 아키텍처 리뷰 체크리스트

**Plan 단계** (지금):
- [ ] Tailwind CSS responsive 접근법 검토
- [ ] Web Notifications API 권한 처리 검토
- [ ] Service Worker 캐시 전략 검토
- [ ] 성능 영향도 분석

**Review 단계** (Gemini 피드백):
- [ ] 아키텍처 승인
- [ ] 기술 결정사항 검증
- [ ] 리스크 식별 및 완화책

**Implement 단계**:
- [ ] 3가지 phase 순차 구현
- [ ] 각 phase 검증

**CodeReview 단계** (Gemini):
- [ ] 코드 품질 검토
- [ ] 타입 안정성 확인
- [ ] 에러 처리 검증

**Document 단계**:
- [ ] NEXT_STEPS.md 업데이트
- [ ] Sprint 완료 보고서 작성

---

**Next**: Gemini에 이 계획 리뷰 요청 → 피드백 수렴 → 구현 시작
