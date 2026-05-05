import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

interface GuardianEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'warning';
  details?: { message?: string };
  auto_response?: { action: string; status: string };
}

const mockEventTemplates: GuardianEvent[] = [
  {
    event_id: 'evt-001',
    timestamp: new Date().toISOString(),
    event_type: 'ec2_unauthorized_access',
    severity: 'critical',
    details: { message: 'Unauthorized SSH attempt detected on instance' },
  },
  {
    event_id: 'evt-002',
    timestamp: new Date().toISOString(),
    event_type: 's3_public_bucket_detected',
    severity: 'high',
    details: { message: 'S3 bucket is publicly accessible' },
  },
  {
    event_id: 'evt-003',
    timestamp: new Date().toISOString(),
    event_type: 'cost_anomaly_detected',
    severity: 'medium',
    details: { message: 'Daily cost exceeded threshold' },
  },
  {
    event_id: 'evt-004',
    timestamp: new Date().toISOString(),
    event_type: 'guardduty_finding',
    severity: 'high',
    details: { message: 'Cryptomining activity detected' },
  },
];

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const { searchParams } = new URL(request.url);
  const accountId = searchParams.get('account_id') || 'default';

  // Create a ReadableStream for SSE
  const stream = new ReadableStream({
    start(controller) {
      // Send initial comment
      controller.enqueue(':comment: SSE stream started\n\n');

      let eventIndex = 0;

      // Send mock events every 2 seconds
      const interval = setInterval(() => {
        if (eventIndex >= mockEventTemplates.length) {
          eventIndex = 0;
        }

        const template = mockEventTemplates[eventIndex];
        const event: GuardianEvent = {
          ...template,
          event_id: `${template.event_id}-${Date.now()}`,
          timestamp: new Date().toISOString(),
        };

        const sseMessage = `event: event\ndata: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(sseMessage);
        eventIndex++;
      }, 2000);

      // Cleanup on close
      return () => clearInterval(interval);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
