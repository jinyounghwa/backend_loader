import { auth } from '@auth';
import { NextRequest, NextResponse } from 'next/server';

// Mock notification events (random security/cost alerts)
const mockNotifications = [
  {
    title: '🚨 보안 경고',
    body: 'EC2 인스턴스에서 비정상적인 접근 시도 감지',
    tag: 'security',
    requireInteraction: true,
  },
  {
    title: '💰 비용 경고',
    body: 'AWS 일일 비용이 $15를 초과했습니다',
    tag: 'cost',
    requireInteraction: false,
  },
  {
    title: '🔒 S3 알림',
    body: '공개 S3 버킷이 감지되었습니다: my-bucket-public',
    tag: 's3',
    requireInteraction: true,
  },
  {
    title: '✅ 자동 대응 완료',
    body: 'i-1234567890 인스턴스가 성공적으로 중지되었습니다',
    tag: 'remediate',
    requireInteraction: false,
  },
  {
    title: '⏰ 정기 점검',
    body: '마지막 점검: 2분 전 | 다음 점검: 58분 뒤',
    tag: 'health',
    requireInteraction: false,
  },
];

export async function GET(request: NextRequest) {
  // 인증 확인 (Gemini 권고)
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // SSE (Server-Sent Events) 응답 설정
  const encoder = new TextEncoder();
  let isClosed = false;

  const customReadable = new ReadableStream({
    async start(controller) {
      // 클라이언트 연결 종료 감지
      request.signal.addEventListener('abort', () => {
        isClosed = true;
        controller.close();
      });

      // 초기 연결 메시지
      try {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'connected' })}\n\n`));
      } catch {
        isClosed = true;
        controller.close();
        return;
      }

      // 30초마다 mock 알림 전송
      const interval = setInterval(() => {
        if (isClosed) {
          clearInterval(interval);
          return;
        }

        try {
          const notification = mockNotifications[Math.floor(Math.random() * mockNotifications.length)];
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(notification)}\n\n`));
        } catch {
          clearInterval(interval);
          isClosed = true;
          controller.close();
        }
      }, 30000);
    },
  });

  return new Response(customReadable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
