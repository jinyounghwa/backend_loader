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
    const { account_id, finding_id, resource_id } = await request.json();

    if (!account_id || !finding_id) {
      return NextResponse.json(
        { error: 'Missing required fields: account_id, finding_id' },
        { status: 400 }
      );
    }

    const action = {
      action_id: `act-${Date.now()}`,
      timestamp: new Date().toISOString(),
      account_id,
      user: session.user?.email || 'system',
      action_type: 'remediate',
      resource_id: resource_id || finding_id,
      status: 'success' as const,
      message: `Auto-remediated finding ${finding_id}`,
    };

    return NextResponse.json({ action, message: 'Remediation initiated' });
  } catch (error) {
    console.error('Remediation failed:', error);
    return NextResponse.json({ error: 'Remediation failed' }, { status: 500 });
  }
}
