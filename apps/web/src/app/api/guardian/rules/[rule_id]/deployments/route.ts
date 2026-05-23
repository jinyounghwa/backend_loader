/**
 * Rule Deployments History API Route (Sprint 35 Phase 2)
 * GET /api/guardian/rules/[rule_id]/deployments
 *
 * Retrieves deployment history for a specific rule
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface DeploymentHistory {
  deployment_id: string;
  rule_id: string;
  status: 'PENDING' | 'ACTIVE' | 'FAILED' | 'ROLLED_BACK';
  deployment_date: string;
  deployed_by?: string;
  error_message?: string;
}

interface DeploymentsResponse {
  success: boolean;
  rule_id: string;
  deployments?: DeploymentHistory[];
  error_message?: string;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { rule_id: string } }
): Promise<NextResponse<DeploymentsResponse>> {
  try {
    const rule_id = params.rule_id;
    const limit = request.nextUrl.searchParams.get('limit') || '10';

    if (!rule_id || rule_id === '[rule_id]') {
      return NextResponse.json({
        success: false,
        rule_id: 'unknown',
        error_message: 'Invalid rule_id parameter',
      }, { status: 400 });
    }

    // Call backend deployment handler
    const deploymentHistory = await fetchDeploymentHistory(rule_id, parseInt(limit));

    return NextResponse.json({
      success: true,
      rule_id,
      deployments: deploymentHistory,
    });

  } catch (error) {
    console.error('Error fetching deployments:', error);
    return NextResponse.json({
      success: false,
      rule_id: 'unknown',
      error_message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }, { status: 500 });
  }
}

/**
 * Fetch deployment history from backend
 * In production, this would query the RuleDeploymentsTable via Lambda
 */
async function fetchDeploymentHistory(
  rule_id: string,
  limit: number
): Promise<DeploymentHistory[]> {
  try {
    // Simulate fetching from backend
    // In production, this would call the Lambda function
    // that queries RuleDeploymentsTable

    // For now, return empty array (will be populated by backend)
    return [];

  } catch (error) {
    console.error('Error fetching deployment history:', error);
    return [];
  }
}
