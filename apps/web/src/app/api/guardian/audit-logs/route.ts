import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export interface AuditLog {
  connection_id: string;
  timestamp: string;
  event_type: '$connect' | '$disconnect' | 'message' | 'broadcast';
  user_id?: string;
  status: string;
  details?: Record<string, any>;
  message_type?: string;
  threat_score?: number;
}

export interface AuditLogsResponse {
  items: AuditLog[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const connectionId = searchParams.get('connection_id');
    const startTime = searchParams.get('start_time');
    const endTime = searchParams.get('end_time');
    const eventType = searchParams.get('event_type');
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');

    if (!connectionId) {
      return NextResponse.json(
        { error: 'Missing required parameter: connection_id' },
        { status: 400 }
      );
    }

    const apiEndpoint = process.env.AUDIT_API_ENDPOINT;
    if (!apiEndpoint) {
      console.error('AUDIT_API_ENDPOINT not configured');
      return NextResponse.json(
        { error: 'Audit API endpoint not configured' },
        { status: 500 }
      );
    }

    // Build query parameters for backend HTTP API
    const queryParams = new URLSearchParams({
      connection_id: connectionId,
      ...(startTime && { start_time: startTime }),
      ...(endTime && { end_time: endTime }),
      ...(eventType && { event_type: eventType }),
    });

    const backendUrl = `${apiEndpoint}?${queryParams.toString()}`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`Backend API error: ${response.status}`, error);
      return NextResponse.json(
        { error: 'Failed to fetch audit logs from backend' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Apply pagination on the frontend
    const items = Array.isArray(data.items) ? data.items : [];
    const paginatedItems = items.slice(offset, offset + limit);
    const total = items.length;

    return NextResponse.json({
      items: paginatedItems,
      count: paginatedItems.length,
      total,
      limit,
      offset,
      hasMore: offset + limit < total,
    } as AuditLogsResponse);
  } catch (error) {
    console.error('Error fetching audit logs:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
