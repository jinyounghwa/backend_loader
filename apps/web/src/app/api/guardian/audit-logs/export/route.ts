import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

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
    const format = searchParams.get('format') || 'json';
    const startTime = searchParams.get('start_time');
    const endTime = searchParams.get('end_time');

    if (!['json', 'csv'].includes(format)) {
      return NextResponse.json(
        { error: 'Invalid format. Use "json" or "csv"' },
        { status: 400 }
      );
    }

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
    queryParams.append('format', format);
    if (startTime) queryParams.append('start_time', startTime);
    if (endTime) queryParams.append('end_time', endTime);

    const backendUrl = `${apiEndpoint}/export?${queryParams.toString()}`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': format === 'json' ? 'application/json' : 'text/csv',
      },
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`Backend API error: ${response.status}`, error);
      return NextResponse.json(
        { error: 'Failed to export logs from backend' },
        { status: response.status }
      );
    }

    const content = await response.text();

    // Return as file download
    const filename = `audit-logs-${new Date().toISOString()}.${format === 'csv' ? 'csv' : 'json'}`;
    const contentType = format === 'csv' ? 'text/csv' : 'application/json';

    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Error exporting logs:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
