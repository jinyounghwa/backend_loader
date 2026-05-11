import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export interface SlackNotificationRequest {
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
    const body: SlackNotificationRequest = await request.json();

    // Slack 메시지 포맷
    const color = {
      HIGH: '#dc2626',
      MEDIUM: '#f59e0b',
      INFO: '#3b82f6',
    }[body.severity];

    const slackMessage = {
      text: `🚨 ${body.severity} Alert - ${body.title}`,
      attachments: [
        {
          color,
          title: body.title,
          text: body.message,
          fields: [
            {
              title: 'Check Type',
              value: body.check_type,
              short: true,
            },
            ...(body.resource_id
              ? [
                  {
                    title: 'Resource ID',
                    value: body.resource_id,
                    short: true,
                  },
                ]
              : []),
            {
              title: 'Timestamp',
              value: new Date().toISOString(),
              short: false,
            },
          ],
        },
      ],
    };

    // 실제 Slack 웹훅이 설정된 경우에만 전송
    const slackWebhookUrl = process.env.SLACK_WEBHOOK_URL;
    if (slackWebhookUrl) {
      await fetch(slackWebhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(slackMessage),
      });
    }

    return NextResponse.json({
      success: true,
      message: 'Notification sent to Slack',
      webhook_configured: !!slackWebhookUrl,
    });
  } catch (error) {
    console.error('Error sending Slack notification:', error);
    return NextResponse.json(
      { error: 'Failed to send notification' },
      { status: 500 }
    );
  }
}
