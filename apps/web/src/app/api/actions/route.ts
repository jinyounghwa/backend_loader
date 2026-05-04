import { auth } from '@auth';
import { NextRequest, NextResponse } from 'next/server';

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

export async function GET(request: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const searchParams = request.nextUrl.searchParams;
  const accountId = searchParams.get('account_id') || 'all';
  const typeFilter = searchParams.get('type') || 'all';
  const statusFilter = searchParams.get('status') || 'all';
  const limit = Math.min(parseInt(searchParams.get('limit') || '10'), 50);

  try {
    let actions: Action[] = [
      {
        action_id: 'act-pending-001',
        timestamp: new Date(Date.now() - 300000).toISOString(),
        account_id: accountId,
        user: session.user?.email || 'system',
        action_type: 'stop_instance' as const,
        resource_id: 'i-9876543210fedcba0',
        status: 'pending' as const,
        message: 'Suspicious EC2 instance detected - pending manual approval',
      },
      {
        action_id: 'act-001',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        account_id: accountId,
        user: session.user?.email || 'system',
        action_type: 'stop_instance' as const,
        resource_id: 'i-0123456789abcdef0',
        status: 'success' as const,
        message: 'EC2 instance stopped due to security violation',
      },
      {
        action_id: 'act-002',
        timestamp: new Date(Date.now() - 7200000).toISOString(),
        account_id: accountId,
        user: session.user?.email || 'system',
        action_type: 'block_bucket' as const,
        resource_id: 'logs-backup-public',
        status: 'success' as const,
        message: 'S3 bucket public access blocked',
      },
      {
        action_id: 'act-003',
        timestamp: new Date(Date.now() - 10800000).toISOString(),
        account_id: accountId,
        user: session.user?.email || 'system',
        action_type: 'remediate' as const,
        resource_id: 'finding-12345',
        status: 'success' as const,
        message: 'GuardDuty finding auto-remediated',
      },
      {
        action_id: 'act-004',
        timestamp: new Date(Date.now() - 14400000).toISOString(),
        account_id: accountId,
        user: session.user?.email || 'system',
        action_type: 'rollback' as const,
        resource_id: 'i-0123456789abcdef0',
        status: 'failed' as const,
        message: 'Failed to rollback action - instance already terminated',
      },
    ];

    // Apply filters
    if (typeFilter !== 'all') {
      actions = actions.filter(a => a.action_type === typeFilter);
    }
    if (statusFilter !== 'all') {
      actions = actions.filter(a => a.status === statusFilter);
    }

    // Apply limit
    actions = actions.slice(0, limit);

    return NextResponse.json({ actions, total: actions.length });
  } catch (error) {
    console.error('Failed to fetch actions:', error);
    return NextResponse.json({ error: 'Failed to fetch actions' }, { status: 500 });
  }
}
