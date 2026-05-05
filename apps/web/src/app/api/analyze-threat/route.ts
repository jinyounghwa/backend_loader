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

export async function POST(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { events } = await request.json();

    if (!events || events.length === 0) {
      return NextResponse.json({ error: 'No events provided' }, { status: 400 });
    }

    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      // Return mock analysis if API key not configured
      return NextResponse.json(MOCK_ANALYSIS);
    }

    const client = new GoogleGenerativeAI(apiKey);
    const model = client.getGenerativeModel({ model: 'gemini-2.0-flash' });

    const prompt = `Analyze these AWS security events and provide:
1. Threat severity (Critical/High/Medium/Low)
2. Root cause analysis
3. Immediate remediation steps (as array)
4. Prevention recommendations (as array)

Events: ${JSON.stringify(events)}

Respond in JSON format with keys: severity, rootCause, remediationSteps, preventionTips`;

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
      remediationSteps: analysis.remediationSteps || [],
      preventionTips: analysis.preventionTips || [],
    });
  } catch (error) {
    console.error('AI analysis error:', error);
    return NextResponse.json(MOCK_ANALYSIS);
  }
}
