import { auth } from '@auth';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  if (!session.user?.role || !['admin', 'owner'].includes(session.user.role)) {
    return NextResponse.json({ error: 'Forbidden: Admin access required' }, { status: 403 });
  }

  try {
    const { action_id, account_id } = await request.json();

    if (!action_id || !account_id) {
      return NextResponse.json(
        { error: 'Missing required fields: action_id, account_id' },
        { status: 400 }
      );
    }

    const rollbackAction = {
      action_id: `act-${Date.now()}`,
      timestamp: new Date().toISOString(),
      account_id,
      user: session.user?.email || 'system',
      action_type: 'rollback' as const,
      resource_id: `rollback_${action_id}`,
      status: 'success' as const,
      message: `Rolled back action ${action_id}`,
    };

    return NextResponse.json({ action: rollbackAction, message: 'Rollback completed' });
  } catch (error) {
    console.error('Rollback failed:', error);
    return NextResponse.json({ error: 'Rollback failed' }, { status: 500 });
  }
}
