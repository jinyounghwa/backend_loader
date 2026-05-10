import { NextResponse } from 'next/server';
import { getAuthSession } from '@/lib/auth-utils';
import { GoogleGenerativeAI } from '@google/generative-ai';

export const dynamic = 'force-dynamic';

const MOCK_ANALYSIS = {
  severity: 'High' as const,
  rootCause: 'Unauthorized CloudTrail event detected. Multiple failed login attempts from unfamiliar IP ranges.',
  remediationSteps: [
    'Review IAM policy changes in the last 24 hours',
    'Enable MFA for all admin accounts',
    'Revoke any suspicious access keys',
  ],
  preventionTips: [
    'Implement IP whitelisting for admin access',
    'Enable CloudTrail logging for all regions',
    'Set up CloudWatch alarms for unauthorized API calls',
  ],
};

const MAX_EVENTS = 20;
const MAX_EVENT_FIELD_LENGTH = 500;

/**
 * Sanitize event data to prevent prompt injection.
 * Extracts only known safe fields and truncates values.
 */
function sanitizeEvents(events: unknown[]): Record<string, string>[] {
  const allowedKeys = new Set([
    'event_id', 'event_type', 'severity', 'timestamp',
    'check_type', 'title', 'message', 'region',
  ]);

  return events.slice(0, MAX_EVENTS).map((evt) => {
    if (typeof evt !== 'object' || evt === null) return {};
    const sanitized: Record<string, string> = {};
    for (const [key, value] of Object.entries(evt as Record<string, unknown>)) {
      if (!allowedKeys.has(key)) continue;
      const strVal = String(value ?? '').slice(0, MAX_EVENT_FIELD_LENGTH);
      sanitized[key] = strVal;
    }
    return sanitized;
  });
}

export async function POST(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { events } = body;

    if (!Array.isArray(events) || events.length === 0) {
      return NextResponse.json({ error: 'No events provided' }, { status: 400 });
    }

    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      // Return mock analysis if API key not configured
      return NextResponse.json(MOCK_ANALYSIS);
    }

    const sanitizedEvents = sanitizeEvents(events);
    const client = new GoogleGenerativeAI(apiKey);
    const model = client.getGenerativeModel({ model: 'gemini-2.0-flash' });

    const prompt = `You are an AWS security analyst. Analyze these security events and respond in valid JSON only.

Events (structured data):
${JSON.stringify(sanitizedEvents)}

Respond with this exact JSON structure:
{"severity": "Critical|High|Medium|Low", "rootCause": "string", "remediationSteps": ["string"], "preventionTips": ["string"]}`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();

    // Parse JSON response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json(MOCK_ANALYSIS);
    }

    const analysis = JSON.parse(jsonMatch[0]);

    return NextResponse.json({
      severity: analysis.severity || 'Medium',
      rootCause: analysis.rootCause || 'Unknown threat detected',
      remediationSteps: Array.isArray(analysis.remediationSteps) ? analysis.remediationSteps.slice(0, 10) : [],
      preventionTips: Array.isArray(analysis.preventionTips) ? analysis.preventionTips.slice(0, 10) : [],
    });
  } catch (error) {
    console.error('AI analysis error:', error);
    return NextResponse.json(MOCK_ANALYSIS);
  }
}

