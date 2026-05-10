import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export async function GET() {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    // AWS Guardian v1.3.0 상태
    const status = {
      version: '1.3.0',
      timestamp: new Date().toISOString(),
      ec2: {
        total_instances: 8,
        running: 6,
        stopped: 2,
        unauthorized_regions: 0,
        security_issues: 0,
        status: 'healthy' as const,
      },
      s3: {
        total_buckets: 15,
        secure_buckets: 14,
        public_buckets: 0,
        encryption_enabled: 15,
        versioning_enabled: 12,
        status: 'healthy' as const,
      },
      cost: {
        daily_cost: 15.50,
        daily_threshold: 10.0,
        monthly_estimate: 465.0,
        within_budget: false,
        trend: 'up' as const,
        status: 'alert' as const,
      },
      cache: {
        backend: 'redis',
        hit_rate: 0.68,
        connected: true,
        status: 'healthy' as const,
      },
      lambda: {
        last_execution: new Date(Date.now() - 3600000).toISOString(),
        execution_time_ms: 1240,
        error_count: 0,
        status: 'healthy' as const,
      },
      overall_health: 'warning' as const,
    };

    return NextResponse.json(status);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch status' },
      { status: 500 }
    );
  }
}
