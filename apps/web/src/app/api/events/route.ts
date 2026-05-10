import { NextResponse } from 'next/server';
import { getAuthSession } from '@/lib/auth-utils';
import {
  getRecentEvents,
  getEventsByGSI,
  getEventsByType,
  getEventsBySeverity,
  getLatestCheckResultOptimized,
} from '@/lib/dynamodb';
import { mockEvents } from '@/lib/mock-data';
import type { DynamoEventItem, GuardianEvent } from '@/types/guardian';

export const dynamic = 'force-dynamic';

/**
 * Transform DynamoDB items to GuardianEvent format
 */
function transformEvents(rawEvents: any[]): GuardianEvent[] {
  return rawEvents.map((item, i) => {
    const ddbItem = item as unknown as DynamoEventItem;
    const parsedDetails = typeof ddbItem.details === 'string' ? JSON.parse(ddbItem.details) : ddbItem.details;
    return {
      event_id: ddbItem.event_id || `evt-${ddbItem.timestamp}-${i}`,
      event_type: (ddbItem.action_type ? 'auto_response' : ddbItem.event_type) as GuardianEvent['event_type'],
      severity: ddbItem.severity as GuardianEvent['severity'],
      timestamp: ddbItem.timestamp,
      details: parsedDetails,
      auto_response: ddbItem.action_type
        ? { action: ddbItem.action_type, resource_id: ddbItem.resource_id || '', status: (ddbItem.status as 'success' | 'failed') || 'success' }
        : undefined,
    };
  });
}

// Allowed filter values to prevent arbitrary DynamoDB GSI key injection
const ALLOWED_EVENT_TYPES = new Set(['all', 'cost', 'ec2', 's3', 'cloudtrail', 'iam', 'guardduty', 'check_result', 'auto_response', 'summary']);
const ALLOWED_SEVERITIES = new Set(['all', 'info', 'low', 'medium', 'high', 'critical', 'warning', 'INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
const MAX_HOURS = 168; // 7 days max
const MIN_HOURS = 1;

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const hoursRaw = parseInt(searchParams.get('hours') || '24', 10);
    const hours = Number.isNaN(hoursRaw) ? 24 : Math.min(Math.max(hoursRaw, MIN_HOURS), MAX_HOURS);
    const typeFilter = searchParams.get('type') || 'all';
    const severityFilter = searchParams.get('severity') || 'all';

    // Validate filter values against allow-list
    if (!ALLOWED_EVENT_TYPES.has(typeFilter)) {
      return NextResponse.json({ error: 'Invalid type filter' }, { status: 400 });
    }
    if (!ALLOWED_SEVERITIES.has(severityFilter)) {
      return NextResponse.json({ error: 'Invalid severity filter' }, { status: 400 });
    }

    // ============================================================================
    // Query Strategy: Use GSI for optimal performance
    // ============================================================================
    // If specific filter is provided, use targeted GSI Query instead of full Scan
    // This dramatically reduces RCU consumption and improves response time

    let rawEvents: any[] = [];

    if (typeFilter !== 'all') {
      // ✅ Query TypeTimestampIndex GSI
      rawEvents = await getEventsByType(typeFilter, hours);
    } else if (severityFilter !== 'all') {
      // ✅ Query SeverityTimestampIndex GSI
      rawEvents = await getEventsBySeverity(severityFilter, hours);
    } else {
      // ✅ Query AllEventsIndex GSI for all recent events
      rawEvents = await getEventsByGSI(hours);
    }

    // Fallback to mock data if no real data
    if (rawEvents.length === 0) {
      return NextResponse.json({ events: mockEvents, total: mockEvents.length });
    }

    // Transform to frontend format
    let events: GuardianEvent[] = transformEvents(rawEvents);

    // Apply secondary filters if both type and severity are specified
    if (typeFilter !== 'all' && severityFilter !== 'all') {
      events = events.filter(e => e.severity === severityFilter);
    }

    return NextResponse.json({ events, total: events.length });
  } catch (error) {
    console.error('Error fetching events:', error);
    return NextResponse.json({ events: mockEvents, total: mockEvents.length });
  }
}
