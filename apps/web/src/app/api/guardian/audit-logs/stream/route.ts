import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

interface AuditLogEvent {
  type: 'audit_log_created' | 'audit_log_modified' | 'audit_log_removed';
  data: Record<string, any>;
  timestamp: string;
}

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const accountId = searchParams.get('account_id');
  const connectionId = searchParams.get('connection_id');

  if (!accountId && !connectionId) {
    return NextResponse.json(
      { error: 'Missing required parameter: account_id or connection_id' },
      { status: 400 }
    );
  }

  const encoder = new TextEncoder();
  let isClosed = false;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const sendMessage = (event: AuditLogEvent) => {
        if (isClosed) return;

        const message = `data: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(encoder.encode(message));
      };

      const sendHeartbeat = () => {
        if (isClosed) return;
        controller.enqueue(encoder.encode(': heartbeat\n\n'));
      };

      const stopStream = () => {
        isClosed = true;
        controller.close();
      };

      // Connection established
      const connectedMessage: AuditLogEvent = {
        type: 'audit_log_created',
        data: {
          status: 'connected',
          accountId: accountId || 'all',
          connectionId: connectionId || 'all',
        },
        timestamp: new Date().toISOString(),
      };
      sendMessage(connectedMessage);

      // Heartbeat every 30 seconds
      const heartbeatInterval = setInterval(() => {
        sendHeartbeat();
      }, 30000);

      // Cleanup on request close
      const onClose = () => {
        clearInterval(heartbeatInterval);
        stopStream();
      };

      request.signal.addEventListener('abort', onClose);

      // Keep connection open
      setTimeout(() => {
        if (!isClosed) {
          clearInterval(heartbeatInterval);
          stopStream();
        }
      }, 3600000); // 1 hour timeout
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
    },
  });
}
