import { NextResponse } from 'next/server';
import { auth } from '@auth';

interface CostData {
  region: string;
  today_cost: number;
  monthly_cost: number;
  increase_percent: number;
  is_anomaly: boolean;
}

interface AnomalyDetection {
  detected: boolean;
  region: string;
  today_cost: number;
  avg_7day: number;
  spike_percent: number;
  daily_impact: number;
  confidence: 'low' | 'medium' | 'high';
}

// Mock cost history (production uses DynamoDB)
const mockCostHistory: Record<string, number[]> = {
  'ap-northeast-1': [45.2, 48.5, 42.1, 46.8, 44.3, 47.2, 43.9],
  'us-east-1': [120.5, 125.3, 118.2, 122.4, 119.8, 124.1, 121.3],
  'eu-west-1': [85.2, 88.4, 82.1, 86.3, 84.5, 87.2, 83.8],
};

export async function POST(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { regions, costData } = (await request.json()) as {
      regions: string[];
      costData: Record<string, CostData>;
    };

    const anomalies: AnomalyDetection[] = [];

    for (const region of regions) {
      const cost = costData[region];
      if (!cost) continue;

      const history = mockCostHistory[region] || [];
      if (history.length < 3) continue;

      const avg = history.reduce((a, b) => a + b, 0) / history.length;
      const threshold = avg * 1.2;

      if (cost.today_cost > threshold) {
        const spike = ((cost.today_cost - avg) / avg) * 100;
        anomalies.push({
          detected: true,
          region,
          today_cost: cost.today_cost,
          avg_7day: parseFloat(avg.toFixed(2)),
          spike_percent: parseFloat(spike.toFixed(2)),
          daily_impact: parseFloat((cost.today_cost - avg).toFixed(2)),
          confidence: spike > 30 ? 'high' : 'medium',
        });
      }
    }

    return NextResponse.json({
      success: true,
      anomalies,
      count: anomalies.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error detecting cost anomalies:', error);
    return NextResponse.json(
      { error: 'Failed to detect anomalies' },
      { status: 500 }
    );
  }
}
