import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest } from 'next/server';

export const runtime = 'nodejs';

interface StreamEvent {
  id: string;
  timestamp: string;
  severity: 'HIGH' | 'MEDIUM' | 'INFO';
  check_type: string;
  title: string;
  message: string;
  details: Record<string, any>;
}

function generateMockEvent(): StreamEvent {
  const checkTypes = ['cost', 'ec2', 's3', 'cloudtrail', 'iam'];
  const severities = ['HIGH', 'MEDIUM', 'INFO'] as const;
  const messages: Record<string, string[]> = {
    cost: [
      'Daily cost $20.00 exceeds threshold $10.00',
      'Monthly budget projection updated',
      'Unusual spending pattern detected',
    ],
    ec2: [
      'New EC2 instance launched in ap-northeast-1',
      'Instance security group modified',
      'EC2 auto-scaling activity detected',
    ],
    s3: [
      'S3 bucket created: new-data-bucket',
      'Bucket permissions modified',
      'S3 access logs configuration changed',
    ],
    cloudtrail: [
      'CloudTrail activity spike detected',
      'New IAM role created',
      'Password policy modified',
    ],
    iam: [
      'New IAM user created',
      'Permissions policy updated',
      'Access key rotation',
    ],
  };

  const checkType = checkTypes[Math.floor(Math.random() * checkTypes.length)];
  const severity = severities[Math.floor(Math.random() * severities.length)];
  const message = messages[checkType][Math.floor(Math.random() * messages[checkType].length)];

  return {
    id: `evt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
    severity,
    check_type: checkType,
    title: `${checkType.toUpperCase()} Alert`,
    message,
    details: {},
  };
}

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // SSE 헤더 설정
  const headers = {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  };

  const encoder = new TextEncoder();

  const readableStream = new ReadableStream({
    async start(controller) {
      // 초기 연결 확인
      controller.enqueue(encoder.encode(':connected\n\n'));

      // 주기적으로 이벤트 전송
      const interval = setInterval(() => {
        // 30% 확률로 새로운 이벤트 생성 및 전송
        if (Math.random() < 0.3) {
          const event = generateMockEvent();
          const data = `data: ${JSON.stringify(event)}\n\n`;
          controller.enqueue(encoder.encode(data));
        }
      }, 5000);

      // 요청이 닫혀도 인터벌 정리
      const cleanup = () => {
        clearInterval(interval);
        controller.close();
      };

      request.signal.addEventListener('abort', cleanup);
    },
  });

  return new Response(readableStream, { headers });
}
