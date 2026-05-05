import { NextResponse } from 'next/server';
import { getAuthSession } from '@/lib/auth-utils';

interface RuleMetric {
  rule_id: string;
  action_type: string;
  total_actions: number;
  successful_actions: number;
  success_rate: number;
  resolved_issues: number;
  resolution_rate: number;
  effectiveness_score: number;
}

// Mock metrics (production uses DynamoDB)
const mockMetrics: RuleMetric[] = [
  {
    rule_id: 'rule-001',
    action_type: 'stop_instance',
    total_actions: 15,
    successful_actions: 14,
    success_rate: 0.93,
    resolved_issues: 13,
    resolution_rate: 0.87,
    effectiveness_score: 0.90,
  },
  {
    rule_id: 'rule-002',
    action_type: 'stop_instance',
    total_actions: 8,
    successful_actions: 7,
    success_rate: 0.88,
    resolved_issues: 6,
    resolution_rate: 0.75,
    effectiveness_score: 0.82,
  },
  {
    rule_id: 'rule-003',
    action_type: 'block_bucket',
    total_actions: 22,
    successful_actions: 22,
    success_rate: 1.0,
    resolved_issues: 21,
    resolution_rate: 0.95,
    effectiveness_score: 0.98,
  },
];

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const rule_id = searchParams.get('rule_id');
    const days = parseInt(searchParams.get('days') || '30');

    let metrics: RuleMetric[] = mockMetrics;

    if (rule_id) {
      metrics = metrics.filter(m => m.rule_id === rule_id);
    }

    const avgEffectiveness = metrics.length > 0
      ? metrics.reduce((sum, m) => sum + m.effectiveness_score, 0) / metrics.length
      : 0;

    return NextResponse.json({
      success: true,
      metrics,
      summary: {
        total_rules: metrics.length,
        avg_effectiveness_score: parseFloat(avgEffectiveness.toFixed(2)),
        avg_success_rate: parseFloat(
          (metrics.reduce((sum, m) => sum + m.success_rate, 0) / metrics.length).toFixed(2)
        ),
        avg_resolution_rate: parseFloat(
          (metrics.reduce((sum, m) => sum + m.resolution_rate, 0) / metrics.length).toFixed(2)
        ),
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching metrics:', error);
    return NextResponse.json(
      { error: 'Failed to fetch metrics' },
      { status: 500 }
    );
  }
}
