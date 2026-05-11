import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') || '10');

    // Mock 자동 대응 기록
    const actions = [
      {
        id: 'act-001',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        action_type: 'ec2_stop',
        resource_id: 'i-1234567890abcdef0',
        status: 'success',
        message: 'Instance stopped successfully',
      },
      {
        id: 'act-002',
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        action_type: 's3_block_public',
        resource_id: 'my-bucket-name',
        status: 'success',
        message: 'Public access blocked successfully',
      },
      {
        id: 'act-003',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        action_type: 'ec2_stop',
        resource_id: 'i-0987654321fedcba0',
        status: 'success',
        message: 'Instance stopped successfully',
      },
      {
        id: 'act-004',
        timestamp: new Date(Date.now() - 7200000).toISOString(),
        action_type: 's3_block_public',
        resource_id: 'another-bucket',
        status: 'success',
        message: 'Public access blocked successfully',
      },
    ];

    const sliced_actions = actions.slice(0, limit);

    return NextResponse.json({
      actions: sliced_actions,
      total: actions.length,
      limit,
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch actions' },
      { status: 500 }
    );
  }
}
