import { NextResponse } from 'next/server';
import { getLatestCheckResult, getRecentEvents } from '@/lib/dynamodb';
import { mockCostData, mockEC2Data, mockS3Data, mockEvents } from '@/lib/mock-data';
import type { CheckResultDetails, DashboardSummary, DynamoEventItem, GuardianEvent } from '@/types/guardian';

export const dynamic = 'force-dynamic';

function generateNextCheckTime(): string {
  return new Date(Date.now() + 60 * 60 * 1000).toISOString();
}

function buildFallbackSummary(): DashboardSummary {
  return {
    cost: mockCostData,
    ec2: mockEC2Data,
    s3: mockS3Data,
    recent_events: mockEvents.slice(0, 5),
    last_check: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    next_check: generateNextCheckTime(),
    system_health: 'warning',
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

export async function GET() {
  try {
    const [checkResult, rawEvents] = await Promise.all([
      getLatestCheckResult(),
      getRecentEvents(24),
    ]);

    if (!checkResult) {
      return NextResponse.json(buildFallbackSummary());
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
    };

    return NextResponse.json(summary);
  } catch {
    return NextResponse.json(buildFallbackSummary());
  }
}
