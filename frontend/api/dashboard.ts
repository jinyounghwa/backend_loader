/**
 * Dashboard API endpoints
 * Serves data to the Next.js dashboard frontend
 */

import { NextApiRequest, NextApiResponse } from 'next';

interface Threat {
  id: string;
  type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  timestamp: string;
  resource_id?: string;
  description?: string;
}

interface CostTrend {
  date: string;
  amount: number;
  forecast?: number;
}

interface DashboardData {
  threats: Threat[];
  cost_trend: CostTrend[];
  iam_findings: any[];
  cloudtrail_events: any[];
  summary: {
    critical_threats: number;
    total_cost_month: number;
    iam_risk_score: number;
  };
}

/**
 * GET /api/dashboard
 * Fetch complete dashboard data
 */
export async function getDashboardData(): Promise<DashboardData> {
  // Mock data - in production this would fetch from DynamoDB/Lambda
  const threats: Threat[] = [
    {
      id: 'threat-1',
      type: 'MALWARE',
      severity: 'CRITICAL',
      timestamp: new Date().toISOString(),
      resource_id: 'i-12345678',
      description: 'Bitcoin mining detected on EC2'
    },
    {
      id: 'threat-2',
      type: 'UNAUTHORIZED_ACCESS',
      severity: 'HIGH',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      resource_id: 'iam-user-123',
      description: 'Multiple failed login attempts'
    },
    {
      id: 'threat-3',
      type: 'RECON',
      severity: 'MEDIUM',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      resource_id: 'i-87654321',
      description: 'Port scanning detected'
    }
  ];

  const costTrend: CostTrend[] = generateCostTrend();

  return {
    threats,
    cost_trend: costTrend,
    iam_findings: generateIamFindings(),
    cloudtrail_events: generateCloudTrailEvents(),
    summary: {
      critical_threats: threats.filter(t => t.severity === 'CRITICAL').length,
      total_cost_month: costTrend.reduce((sum, c) => sum + c.amount, 0),
      iam_risk_score: calculateIamRisk()
    }
  };
}

/**
 * GET /api/dashboard/threats?filter=severity&value=CRITICAL
 * Fetch filtered threats
 */
export async function getFilteredThreats(
  filter: string,
  value: string
): Promise<Threat[]> {
  const allThreats = (await getDashboardData()).threats;

  if (filter === 'severity') {
    return allThreats.filter(t => t.severity === value);
  } else if (filter === 'type') {
    return allThreats.filter(t => t.type === value);
  }

  return allThreats;
}

/**
 * GET /api/dashboard/cost?period=month
 * Fetch cost trend data
 */
export async function getCostTrend(period: string = 'month'): Promise<CostTrend[]> {
  const data = await getDashboardData();
  return data.cost_trend;
}

/**
 * GET /api/dashboard/iam
 * Fetch IAM analysis data
 */
export async function getIamAnalysis() {
  const data = await getDashboardData();
  return {
    findings: data.iam_findings,
    risk_score: data.summary.iam_risk_score,
    unused_roles: generateUnusedRoles(),
    privilege_escalations: generatePrivilegeEscalations()
  };
}

/**
 * GET /api/dashboard/cloudtrail
 * Fetch CloudTrail event timeline
 */
export async function getCloudTrailEvents(limit: number = 50) {
  const data = await getDashboardData();
  return {
    events: data.cloudtrail_events.slice(0, limit),
    total: data.cloudtrail_events.length
  };
}

/**
 * WebSocket endpoint for real-time updates
 * Subscribe to threat updates
 */
export function subscribeToThreats(onThreat: (threat: Threat) => void) {
  // In production, this would connect to a WebSocket server
  // For now, simulate with intervals
  const interval = setInterval(() => {
    const newThreat: Threat = {
      id: `threat-${Date.now()}`,
      type: ['MALWARE', 'RECON', 'UNAUTHORIZED_ACCESS'][Math.floor(Math.random() * 3)],
      severity: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'][Math.floor(Math.random() * 4)] as any,
      timestamp: new Date().toISOString()
    };
    onThreat(newThreat);
  }, 30000); // New threat every 30 seconds

  return () => clearInterval(interval);
}

// Helper functions

function generateCostTrend(days: number = 30): CostTrend[] {
  const trend: CostTrend[] = [];
  const today = new Date();

  for (let i = days; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);

    const baseAmount = 150 + Math.random() * 100;
    const forecast = baseAmount * 1.1 + Math.random() * 50;

    trend.push({
      date: date.toISOString().split('T')[0],
      amount: Math.round(baseAmount * 100) / 100,
      forecast: Math.round(forecast * 100) / 100
    });
  }

  return trend;
}

function generateIamFindings() {
  return [
    {
      id: 'iam-1',
      type: 'POLICY_ANALYSIS',
      risk_score: 85,
      description: 'AdministratorAccess on service account'
    },
    {
      id: 'iam-2',
      type: 'UNUSED_ROLE',
      risk_score: 45,
      description: 'Lambda role unused for 120 days'
    },
    {
      id: 'iam-3',
      type: 'CROSS_ACCOUNT',
      risk_score: 70,
      description: 'Trust relationship with external account'
    }
  ];
}

function generateCloudTrailEvents() {
  return [
    {
      id: 'ct-1',
      eventName: 'RunInstances',
      timestamp: new Date().toISOString(),
      severity: 'MEDIUM'
    },
    {
      id: 'ct-2',
      eventName: 'PutUserPolicy',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      severity: 'HIGH'
    },
    {
      id: 'ct-3',
      eventName: 'DeleteBucket',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      severity: 'CRITICAL'
    }
  ];
}

function generateUnusedRoles() {
  return [
    { name: 'old-lambda-role', days_unused: 120 },
    { name: 'test-role-backup', days_unused: 95 }
  ];
}

function generatePrivilegeEscalations() {
  return [
    { event: 'AttachUserPolicy', user: 'suspicious-user', policy: 'AdministratorAccess' },
    { event: 'CreateAccessKey', user: 'service-account', policy: 'N/A' }
  ];
}

function calculateIamRisk(): number {
  return Math.round(Math.random() * 100);
}
