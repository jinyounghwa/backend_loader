import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export interface ThreatAnalysis {
  threat_score: number; // 0-10 점수
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  findings: {
    public_buckets: number;
    unauthorized_regions: number;
    high_cost_spike: boolean;
    anomalous_api_activity: boolean;
  };
  recommendations: string[];
  timestamp: string;
}

export async function GET() {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    // 위협 점수 계산 (0-10 scale)
    // - 공개 S3 버킷: 3점
    // - 비인가 리전 EC2: 2점
    // - 높은 비용 증가: 1점
    // - 비정상 API 활동: 2점

    const findings = {
      public_buckets: 0,
      unauthorized_regions: 0,
      high_cost_spike: true,
      anomalous_api_activity: false,
    };

    let threat_score = 0;
    const recommendations: string[] = [];

    if (findings.public_buckets > 0) {
      threat_score += 3;
      recommendations.push('공개 S3 버킷 즉시 차단 필요');
    }

    if (findings.unauthorized_regions > 0) {
      threat_score += 2;
      recommendations.push('비인가 리전의 EC2 인스턴스 종료 권장');
    }

    if (findings.high_cost_spike) {
      threat_score += 1;
      recommendations.push('비용 상승 원인 조사 및 리소스 최적화');
    }

    if (findings.anomalous_api_activity) {
      threat_score += 2;
      recommendations.push('비정상 API 활동 상세 분석 필요');
    }

    threat_score = Math.min(10, threat_score);

    let risk_level: 'low' | 'medium' | 'high' | 'critical';
    if (threat_score <= 2) {
      risk_level = 'low';
    } else if (threat_score <= 4) {
      risk_level = 'medium';
    } else if (threat_score <= 7) {
      risk_level = 'high';
    } else {
      risk_level = 'critical';
    }

    if (recommendations.length === 0) {
      recommendations.push('모든 보안 점검 통과');
    }

    const analysis: ThreatAnalysis = {
      threat_score,
      risk_level,
      findings,
      recommendations,
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(analysis);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to analyze threats' },
      { status: 500 }
    );
  }
}
