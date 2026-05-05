import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

interface AuditLog {
  log_id: string;
  timestamp: string;
  user: string;
  action: string;
  resource_id: string;
  status: 'success' | 'failed';
  details?: Record<string, unknown>;
}

export const dynamic = 'force-dynamic';

// Mock audit logs for demonstration
const mockAuditLogs: AuditLog[] = [
  {
    log_id: 'log-001',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    user: 'system',
    action: 'stop_instance',
    resource_id: 'i-0123456789abcdef0',
    status: 'success',
    details: { region: 'ap-northeast-1', reason: 'Security violation detected' },
  },
  {
    log_id: 'log-002',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    user: 'admin@example.com',
    action: 'block_bucket',
    resource_id: 'logs-backup-public',
    status: 'success',
    details: { bucket_region: 'us-east-1', block_type: 'PublicAccessBlockConfiguration' },
  },
  {
    log_id: 'log-003',
    timestamp: new Date(Date.now() - 10800000).toISOString(),
    user: 'system',
    action: 'remediate',
    resource_id: 'finding-12345',
    status: 'success',
    details: { finding_type: 'UnauthorizedAccess', remediation_method: 'Auto' },
  },
  {
    log_id: 'log-004',
    timestamp: new Date(Date.now() - 14400000).toISOString(),
    user: 'admin@example.com',
    action: 'rollback',
    resource_id: 'i-0123456789abcdef0',
    status: 'failed',
    details: { error: 'Instance already terminated', attempt: 1 },
  },
];

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 100);
    const user = searchParams.get('user');
    const action = searchParams.get('action');

    let logs = [...mockAuditLogs];

    // Apply filters
    if (user) {
      logs = logs.filter(log => log.user === user);
    }
    if (action) {
      logs = logs.filter(log => log.action === action);
    }

    // Sort by timestamp (newest first) and apply limit
    logs = logs
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, limit);

    return NextResponse.json({ logs, total: logs.length });
  } catch (error) {
    console.error('Error fetching audit logs:', error);
    return NextResponse.json({ error: 'Failed to fetch audit logs' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { user, action, resource_id, status, details } = body;

    if (!user || !action || !resource_id) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const log: AuditLog = {
      log_id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      user,
      action,
      resource_id,
      status: status || 'success',
      details,
    };

    // In production, save to DynamoDB here
    // For now, just return success
    return NextResponse.json({ success: true, log });
  } catch (error) {
    console.error('Error creating audit log:', error);
    return NextResponse.json({ error: 'Failed to create audit log' }, { status: 500 });
  }
}
