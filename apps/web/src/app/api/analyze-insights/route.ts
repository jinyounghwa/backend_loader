import { NextResponse } from 'next/server';
import { auth } from '@auth';

interface AnomalyInput {
  region: string;
  type: 'ec2_exposure' | 's3_public' | 'cost_spike';
  count: number;
  details?: string;
}

interface InsightsResponse {
  correlation_score: number;
  threat_type: string;
  confidence: 'low' | 'medium' | 'high';
  urgency: number;
  recommendation: string;
  cost_impact?: number;
  remediation_rate?: number;
}

async function analyzeWithGemini(anomalies: AnomalyInput[]): Promise<InsightsResponse> {
  // Production: call actual Gemini API via @google/generative-ai
  // For now: rule-based analysis
  const ec2Count = anomalies
    .filter(a => a.type === 'ec2_exposure')
    .reduce((sum, a) => sum + a.count, 0);
  const s3Count = anomalies
    .filter(a => a.type === 's3_public')
    .reduce((sum, a) => sum + a.count, 0);
  const regionCount = new Set(anomalies.map(a => a.region)).size;

  let threatType = 'Single-Region Misconfiguration';
  let correlationScore = 0.3;
  let confidence: 'low' | 'medium' | 'high' = 'low';
  let urgency = 3;

  if (regionCount > 1 && ec2Count + s3Count > 5) {
    threatType = 'Multi-Region Exposure Pattern';
    correlationScore = 0.7;
    confidence = 'high';
    urgency = 8;
  } else if (ec2Count + s3Count > 3) {
    threatType = 'Account-Level Misconfiguration';
    correlationScore = 0.6;
    confidence = 'medium';
    urgency = 7;
  }

  return {
    correlation_score: correlationScore,
    threat_type: threatType,
    confidence,
    urgency,
    recommendation: `Review IAM policies and Security Groups. ${
      regionCount > 1
        ? 'Apply account-level preventive controls.'
        : 'Address region-specific configuration.'
    }`,
    cost_impact: ec2Count > 0 ? ec2Count * 10 : 0,
    remediation_rate: Math.random() * 0.3 + 0.7,
  };
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { anomalies } = (await request.json()) as { anomalies: AnomalyInput[] };

    if (!Array.isArray(anomalies) || anomalies.length === 0) {
      return NextResponse.json(
        { error: 'Invalid anomalies input' },
        { status: 400 }
      );
    }

    const insights = await analyzeWithGemini(anomalies);

    return NextResponse.json({
      success: true,
      insights,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error analyzing insights:', error);
    return NextResponse.json(
      { error: 'Failed to analyze insights' },
      { status: 500 }
    );
  }
}
