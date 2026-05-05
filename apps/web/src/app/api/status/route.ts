import { NextResponse } from 'next/server';
import { auth } from '@auth';
import { getLatestCheckResult, getRecentEvents } from '@/lib/dynamodb';
import { mockCostData, mockEC2Data, mockS3Data, mockEvents } from '@/lib/mock-data';
import type { CheckResultDetails, DashboardSummary, DynamoEventItem, GuardianEvent, MultiRegionSummary } from '@/types/guardian';

export const dynamic = 'force-dynamic';
const CHECK_INTERVAL_MINUTES = 60;
const STALE_THRESHOLD_MINUTES = 65; // 60min + 5min buffer

function generateNextCheckTime(): string {
  return new Date(Date.now() + CHECK_INTERVAL_MINUTES * 60 * 1000).toISOString();
}

function isStaleData(lastCheckTime: string): boolean {
  const lastCheckMs = new Date(lastCheckTime).getTime();
  const ageMinutes = (Date.now() - lastCheckMs) / (1000 * 60);
  return ageMinutes > STALE_THRESHOLD_MINUTES;
}

function buildFallbackSummary(region: string = 'ap-northeast-1'): DashboardSummary {
  return {
    cost: mockCostData,
    ec2: mockEC2Data,
    s3: mockS3Data,
    recent_events: mockEvents.slice(0, 5),
    last_check: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    next_check: generateNextCheckTime(),
    system_health: 'warning',
    region,
    is_stale: false,
  };
}

function ddbItemToGuardianEvent(item: DynamoEventItem, index: number): GuardianEvent {
  const parsedDetails = typeof item.details === 'string' ? JSON.parse(item.details) : item.details;
  return {
    event_id: `evt-${item.timestamp}-${index}`,
    event_type: (item.action_type ? 'auto_response' : item.event_type) as GuardianEvent['event_type'],
    severity: item.severity as GuardianEvent['severity'],
    timestamp: item.timestamp,
    details: parsedDetails,
    auto_response: item.action_type
      ? { action: item.action_type, resource_id: item.resource_id || '', status: (item.status as 'success' | 'failed') || 'success' }
      : undefined,
  };
}

async function fetchRegionData(region: string): Promise<DashboardSummary | null> {
  try {
    const [checkResult, rawEvents] = await Promise.all([
      getLatestCheckResult(),
      getRecentEvents(24),
    ]);

    if (!checkResult) {
      return null;
    }

    const details: CheckResultDetails = typeof checkResult.details === 'string'
      ? JSON.parse(checkResult.details)
      : checkResult.details;

    const recent_events = rawEvents.map((item, i) =>
      ddbItemToGuardianEvent(item as unknown as DynamoEventItem, i)
    );

    const summary: DashboardSummary = {
      cost: details.cost,
      ec2: details.ec2,
      s3: details.s3,
      recent_events: recent_events.slice(0, 5),
      last_check: details.last_check,
      next_check: generateNextCheckTime(),
      system_health: details.system_health,
      region,
      is_stale: isStaleData(details.last_check),
    };

    return summary;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const regionsParam = searchParams.get('regions');
    const regions = regionsParam
      ? regionsParam.split(',').filter(r => r.trim())
      : ['ap-northeast-1'];

    // Single region mode (backward compatibility)
    if (regions.length === 1) {
      const region = regions[0];
      const data = await fetchRegionData(region);
      return NextResponse.json(data || buildFallbackSummary(region));
    }

    // Multi-region mode
    const results = await Promise.allSettled(
      regions.map(region => fetchRegionData(region))
    );

    const summaries: DashboardSummary[] = [];
    const errors: Record<string, string> = {};

    results.forEach((result, index) => {
      const region = regions[index];
      if (result.status === 'fulfilled' && result.value) {
        summaries.push(result.value);
      } else if (result.status === 'rejected') {
        errors[region] = 'Failed to fetch region data';
        summaries.push(buildFallbackSummary(region));
      } else {
        summaries.push(buildFallbackSummary(region));
      }
    });

    const multiRegionSummary: MultiRegionSummary = {
      regions: summaries,
      last_check: new Date().toISOString(),
      errors,
    };

    return NextResponse.json(multiRegionSummary);
  } catch {
    return NextResponse.json(buildFallbackSummary());
  }
}
