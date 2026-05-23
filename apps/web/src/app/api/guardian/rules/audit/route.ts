/**
 * Rule Audit Logs API Route (Sprint 35 Phase 4)
 * GET /api/guardian/rules/audit
 *
 * Retrieves audit logs for rules with filtering
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface AuditLogEntry {
  rule_id: string;
  audit_id: string;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'DEPLOY' | 'ROLLBACK';
  timestamp: string;
  user_id?: string;
  status: 'SUCCESS' | 'FAILURE';
  error_message?: string;
  details?: Record<string, any>;
}

interface AuditLogsResponse {
  success: boolean;
  logs?: AuditLogEntry[];
  summary?: {
    total_logs: number;
    action_counts: Record<string, number>;
    status_counts: Record<string, number>;
  };
  error_message?: string;
}

export async function GET(request: NextRequest): Promise<NextResponse<AuditLogsResponse>> {
  try {
    const searchParams = request.nextUrl.searchParams;
    const rule_id = searchParams.get('rule_id');
    const limit = parseInt(searchParams.get('limit') || '20');
    const action = searchParams.get('action');
    const start_time = searchParams.get('start_time');
    const end_time = searchParams.get('end_time');

    if (!rule_id) {
      return NextResponse.json({
        success: false,
        error_message: 'Missing rule_id parameter',
      }, { status: 400 });
    }

    // Call backend audit handler
    const auditLogs = await fetchAuditLogs({
      rule_id,
      limit,
      action,
      start_time,
      end_time,
    });

    // Compute summary
    const actionCounts: Record<string, number> = {};
    const statusCounts: Record<string, number> = { SUCCESS: 0, FAILURE: 0 };

    for (const log of auditLogs) {
      actionCounts[log.action] = (actionCounts[log.action] || 0) + 1;
      statusCounts[log.status] = (statusCounts[log.status] || 0) + 1;
    }

    return NextResponse.json({
      success: true,
      logs: auditLogs,
      summary: {
        total_logs: auditLogs.length,
        action_counts: actionCounts,
        status_counts: statusCounts,
      },
    });

  } catch (error) {
    console.error('Error fetching audit logs:', error);
    return NextResponse.json({
      success: false,
      error_message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }, { status: 500 });
  }
}

/**
 * Fetch audit logs from backend
 * In production, this would query the RuleAuditTable via Lambda
 */
async function fetchAuditLogs(params: any): Promise<AuditLogEntry[]> {
  try {
    // Simulate fetching from backend
    // In production, this would call the Lambda function
    // that queries the rule audit logs table

    // For now, return empty array (will be populated by backend)
    return [];

  } catch (error) {
    console.error('Error fetching audit logs:', error);
    return [];
  }
}
