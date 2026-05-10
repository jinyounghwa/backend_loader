import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') || '20');
    const severity = searchParams.get('severity');

    // Mock 이벤트 데이터
    const all_events = [
      {
        id: 'evt-001',
        timestamp: new Date(Date.now() - 60000).toISOString(),
        severity: 'HIGH' as const,
        check_type: 'cost',
        title: 'Cost Threshold Exceeded',
        message: 'Daily cost $15.50 exceeds threshold $10.00',
        details: { daily_cost: 15.5, threshold: 10.0 },
      },
      {
        id: 'evt-002',
        timestamp: new Date(Date.now() - 120000).toISOString(),
        severity: 'INFO' as const,
        check_type: 'ec2',
        title: 'EC2 Security Check',
        message: 'All EC2 instances are in authorized regions',
        details: { regions: ['us-east-1', 'ap-northeast-2'], instances: 6 },
      },
      {
        id: 'evt-003',
        timestamp: new Date(Date.now() - 180000).toISOString(),
        severity: 'INFO' as const,
        check_type: 's3',
        title: 'S3 Security Check',
        message: 'All S3 buckets are secure (no public access)',
        details: { total_buckets: 15, public_buckets: 0 },
      },
      {
        id: 'evt-004',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        severity: 'MEDIUM' as const,
        check_type: 'cloudtrail',
        title: 'CloudTrail Activity',
        message: '12 API calls detected in the last hour',
        details: { call_count: 12, services: ['ec2', 's3', 'iam'] },
      },
    ];

    // 필터링
    let filtered_events = all_events;
    if (severity) {
      filtered_events = all_events.filter((e) => e.severity === severity);
    }

    // 제한
    const events = filtered_events.slice(0, limit);

    return NextResponse.json({
      events,
      total: all_events.length,
      filtered: filtered_events.length,
      limit,
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch events' },
      { status: 500 }
    );
  }
}
