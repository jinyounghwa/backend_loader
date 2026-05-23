import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export interface AuditStatistics {
  total_events: number;
  event_types: Record<string, number>;
  status_distribution: Record<string, number>;
  hourly_distribution: Record<string, number>;
  user_distribution: Record<string, number>;
  top_connections: Array<{ connection_id: string; count: number }>;
  top_accounts: Array<{ account_id: string; count: number }>;
  success_rate: number;
  time_range: {
    start: string;
    end: string;
  };
}

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const accountId = searchParams.get('account_id');
    const connectionId = searchParams.get('connection_id');
    const startTime = searchParams.get('start_time');
    const endTime = searchParams.get('end_time');

    if (!accountId && !connectionId) {
      return NextResponse.json(
        { error: 'Missing required parameter: account_id or connection_id' },
        { status: 400 }
      );
    }

    const apiEndpoint = process.env.AUDIT_API_ENDPOINT;
    if (!apiEndpoint) {
      console.error('AUDIT_API_ENDPOINT not configured');
      return NextResponse.json(
        { error: 'API endpoint not configured' },
        { status: 500 }
      );
    }

    // Build query parameters for backend HTTP API
    const queryParams = new URLSearchParams();
    if (accountId) queryParams.append('account_id', accountId);
    if (connectionId) queryParams.append('connection_id', connectionId);
    if (startTime) queryParams.append('start_time', startTime);
    if (endTime) queryParams.append('end_time', endTime);

    const backendUrl = `${apiEndpoint}/statistics?${queryParams.toString()}`;

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
        { error: 'Failed to fetch statistics from backend' },
        { status: response.status }
      );
    }

    const data = (await response.json()) as AuditStatistics;

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Error fetching statistics:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
