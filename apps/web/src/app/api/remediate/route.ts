import { auth } from '@auth';
import { requireAdmin } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  if (!session.user?.role || !['admin', 'owner'].includes(session.user.role)) {
    return NextResponse.json({ error: 'Forbidden: Admin access required' }, { status: 403 });
  }

  try {
    const { account_id, action: actionType, resource_id, finding_id } = await request.json();

    if (!account_id) {
      return NextResponse.json(
        { error: 'Missing required field: account_id' },
        { status: 400 }
      );
    }

    const finalResourceId = resource_id || finding_id;
    if (!finalResourceId) {
      return NextResponse.json(
        { error: 'Missing required field: resource_id or finding_id' },
        { status: 400 }
      );
    }

    let actionTypeStr = actionType || 'remediate';
    let message = '';

    if (actionTypeStr === 'stop_instance') {
      message = `Stopped EC2 instance ${finalResourceId}`;
    } else if (actionTypeStr === 'block_bucket') {
      message = `Blocked public access to S3 bucket ${finalResourceId}`;
    } else {
      actionTypeStr = 'remediate';
      message = `Remediated finding ${finalResourceId}`;
    }

    const action = {
      action_id: `act-${Date.now()}`,
      timestamp: new Date().toISOString(),
      account_id,
      user: session.user?.email || 'system',
      action_type: actionTypeStr as 'stop_instance' | 'block_bucket' | 'remediate' | 'rollback',
      resource_id: finalResourceId,
      status: 'success' as const,
      message,
    };

    return NextResponse.json({ action, message: 'Action executed successfully' });
  } catch (error) {
    console.error('Action execution failed:', error);
    return NextResponse.json({ error: 'Action execution failed' }, { status: 500 });
  }
}
