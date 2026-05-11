import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export interface PagerDutyIncidentRequest {
  severity: 'HIGH' | 'MEDIUM' | 'INFO';
  title: string;
  message: string;
  check_type: string;
  resource_id?: string;
  details?: Record<string, any>;
}

export async function POST(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const body: PagerDutyIncidentRequest = await request.json();

    // CRITICAL 또는 HIGH만 PagerDuty 인시던트 생성
    if (body.severity === 'INFO' || body.severity === 'MEDIUM') {
      return NextResponse.json({
        success: true,
        message: 'Incident not created (severity too low)',
        incident_created: false,
      });
    }

    // PagerDuty 인시던트 포맷
    const urgency = body.severity === 'HIGH' ? 'high' : 'critical';

    const pagerDutyEvent = {
      routing_key: process.env.PAGERDUTY_ROUTING_KEY,
      event_action: 'trigger',
      payload: {
        summary: body.title,
        severity: urgency.toLowerCase(),
        source: 'AWS Guardian',
        custom_details: {
          message: body.message,
          check_type: body.check_type,
          resource_id: body.resource_id,
          details: body.details,
        },
      },
    };

    // 실제 PagerDuty API 키가 설정된 경우에만 전송
    const routingKey = process.env.PAGERDUTY_ROUTING_KEY;
    let incidentCreated = false;

    if (routingKey) {
      const response = await fetch('https://events.pagerduty.com/v2/enqueue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pagerDutyEvent),
      });

      if (response.ok) {
        incidentCreated = true;
      }
    }

    return NextResponse.json({
      success: true,
      message: 'PagerDuty notification processed',
      incident_created: incidentCreated,
      routing_key_configured: !!routingKey,
    });
  } catch (error) {
    console.error('Error creating PagerDuty incident:', error);
    return NextResponse.json(
      { error: 'Failed to create incident' },
      { status: 500 }
    );
  }
}
