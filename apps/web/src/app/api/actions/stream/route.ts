import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

interface Action {
  action_id: string;
  timestamp: string;
  account_id: string;
  user: string;
  action_type: 'stop_instance' | 'block_bucket' | 'remediate' | 'rollback';
  resource_id: string;
  status: 'success' | 'failed' | 'pending';
  message: string;
}

const mockActionTemplates: Action[] = [
  {
    action_id: 'act-success-001',
    timestamp: new Date().toISOString(),
    account_id: 'default',
    user: 'system',
    action_type: 'stop_instance',
    resource_id: 'i-0123456789abcdef0',
    status: 'success',
    message: 'EC2 instance stopped successfully',
  },
  {
    action_id: 'act-success-002',
    timestamp: new Date().toISOString(),
    account_id: 'default',
    user: 'system',
    action_type: 'block_bucket',
    resource_id: 'logs-backup-public',
    status: 'success',
    message: 'S3 bucket public access blocked',
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

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(':comment: Action stream started\n\n');

      let actionIndex = 0;

      // Send mock action completions every 5 seconds
      const interval = setInterval(() => {
        if (actionIndex >= mockActionTemplates.length) {
          actionIndex = 0;
        }

        const template = mockActionTemplates[actionIndex];
        const action: Action = {
          ...template,
          action_id: `${template.action_id}-${Date.now()}`,
          account_id: accountId,
          timestamp: new Date().toISOString(),
          user: session.user?.email || 'system',
        };

        const sseMessage = `event: action\ndata: ${JSON.stringify(action)}\n\n`;
        controller.enqueue(sseMessage);
        actionIndex++;
      }, 5000);

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
