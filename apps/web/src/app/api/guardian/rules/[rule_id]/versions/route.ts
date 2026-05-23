/**
 * Rule Versions API Route (Sprint 35 Phase 3)
 * GET /api/guardian/rules/[rule_id]/versions
 *
 * Retrieves version history for a specific rule
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface RuleVersionInfo {
  version_id: string;
  version_number: number;
  created_at: string;
  created_by?: string;
  change_reason?: string;
}

interface VersionsResponse {
  success: boolean;
  rule_id: string;
  versions?: RuleVersionInfo[];
  error_message?: string;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { rule_id: string } }
): Promise<NextResponse<VersionsResponse>> {
  try {
    const rule_id = params.rule_id;
    const limit = request.nextUrl.searchParams.get('limit') || '20';

    if (!rule_id || rule_id === '[rule_id]') {
      return NextResponse.json({
        success: false,
        rule_id: 'unknown',
        error_message: 'Invalid rule_id parameter',
      }, { status: 400 });
    }

    // Call backend version handler
    const versionHistory = await fetchVersionHistory(rule_id, parseInt(limit));

    return NextResponse.json({
      success: true,
      rule_id,
      versions: versionHistory,
    });

  } catch (error) {
    console.error('Error fetching versions:', error);
    return NextResponse.json({
      success: false,
      rule_id: 'unknown',
      error_message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }, { status: 500 });
  }
}

/**
 * Fetch version history from backend
 * In production, this would query the RuleVersionsTable via Lambda
 */
async function fetchVersionHistory(
  rule_id: string,
  limit: number
): Promise<RuleVersionInfo[]> {
  try {
    // Simulate fetching from backend
    // In production, this would call the Lambda function
    // that queries the rule versions table

    // For now, return empty array (will be populated by backend)
    return [];

  } catch (error) {
    console.error('Error fetching version history:', error);
    return [];
  }
}
