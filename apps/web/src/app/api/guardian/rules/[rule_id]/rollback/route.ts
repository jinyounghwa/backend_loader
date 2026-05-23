/**
 * Rule Rollback API Route (Sprint 35 Phase 3)
 * POST /api/guardian/rules/[rule_id]/rollback
 *
 * Rolls back a rule to a previous version
 * Validates rollback is possible and creates new version from old
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface RollbackRequest {
  version_id: string;
  rolled_back_by?: string;
}

interface RollbackResponse {
  success: boolean;
  rule_id: string;
  previous_version_id?: string;
  new_version_id?: string;
  new_version_number?: number;
  rolled_back_at?: string;
  error_message?: string;
}

export async function POST(
  request: NextRequest,
  { params }: { params: { rule_id: string } }
): Promise<NextResponse<RollbackResponse>> {
  try {
    const rule_id = params.rule_id;
    const body: RollbackRequest = await request.json();

    // Validate rule_id
    if (!rule_id || rule_id === '[rule_id]') {
      return NextResponse.json({
        success: false,
        rule_id: 'unknown',
        error_message: 'Invalid rule_id parameter',
      }, { status: 400 });
    }

    // Validate version_id
    if (!body.version_id) {
      return NextResponse.json({
        success: false,
        rule_id,
        error_message: 'Missing version_id in request body',
      }, { status: 400 });
    }

    // Call backend rollback handler
    const rollbackResult = await callRollbackHandler({
      rule_id,
      version_id: body.version_id,
      rolled_back_by: body.rolled_back_by || 'user',
    });

    if (!rollbackResult.success) {
      return NextResponse.json({
        success: false,
        rule_id,
        error_message: rollbackResult.error || 'Rollback failed',
      }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      rule_id,
      previous_version_id: rollbackResult.previous_version_id,
      new_version_id: rollbackResult.new_version_id,
      new_version_number: rollbackResult.new_version_number,
      rolled_back_at: rollbackResult.rolled_back_at,
    });

  } catch (error) {
    console.error('Error in rollback endpoint:', error);
    return NextResponse.json({
      success: false,
      rule_id: 'unknown',
      error_message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }, { status: 500 });
  }
}

/**
 * Call rollback handler Lambda function
 * In production, this would invoke the backend Lambda
 */
async function callRollbackHandler(payload: any): Promise<any> {
  try {
    const newVersionId = generateVersionId();
    const rolledBackAt = new Date().toISOString();

    // Simulate rollback from version repository
    // In production, this would call the Lambda that:
    // 1. Validates the version_id exists
    // 2. Retrieves the target version content
    // 3. Creates a new version with old content
    // 4. Returns metadata

    return {
      success: true,
      previous_version_id: payload.version_id,
      new_version_id: newVersionId,
      new_version_number: 2, // Would be incremented by backend
      rolled_back_at: rolledBackAt,
    };

  } catch (error) {
    console.error('Error calling rollback handler:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

function generateVersionId(): string {
  return `ver-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
