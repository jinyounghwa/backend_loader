/**
 * Rule Test-Run API Route (Sprint 35 Phase 1)
 * POST /api/guardian/rules/test-run
 *
 * Executes a rule against sample logs for testing and validation
 * without affecting production detection
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

interface TestRunRequest {
  rule: {
    rule_id?: string;
    rule_type: string;
    condition: Record<string, any>;
    action: Record<string, any>;
    priority?: number;
  };
  test_logs: Array<Record<string, any>>;
  account_id?: string;
}

interface TestRunResponse {
  success: boolean;
  rule_id: string;
  total_logs: number;
  matched_logs: number;
  detected_threats: Array<{
    threat_id: string;
    rule_id: string;
    severity: number;
    account_id?: string;
    timestamp: string;
    message: string;
    evidence_count: number;
  }>;
  execution_time_ms: number;
  error_message?: string;
}

export async function POST(request: NextRequest): Promise<NextResponse<TestRunResponse>> {
  try {
    const body: TestRunRequest = await request.json();

    // Validate request
    if (!body.rule) {
      return NextResponse.json({
        success: false,
        rule_id: 'unknown',
        total_logs: 0,
        matched_logs: 0,
        detected_threats: [],
        execution_time_ms: 0,
        error_message: 'Missing rule in request body',
      }, { status: 400 });
    }

    if (!body.test_logs || !Array.isArray(body.test_logs)) {
      return NextResponse.json({
        success: false,
        rule_id: body.rule.rule_id || 'unknown',
        total_logs: 0,
        matched_logs: 0,
        detected_threats: [],
        execution_time_ms: 0,
        error_message: 'test_logs must be provided as an array',
      }, { status: 400 });
    }

    // Call backend Lambda for rule testing
    const lambdaResponse = await callValidationHandler({
      action: 'test-run',
      rule: body.rule,
      test_logs: body.test_logs,
      account_id: body.account_id,
    });

    if (!lambdaResponse.success && lambdaResponse.error) {
      return NextResponse.json({
        success: false,
        rule_id: body.rule.rule_id || 'unknown',
        total_logs: body.test_logs.length,
        matched_logs: 0,
        detected_threats: [],
        execution_time_ms: 0,
        error_message: lambdaResponse.error,
      }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      rule_id: body.rule.rule_id || 'test-rule',
      total_logs: body.test_logs.length,
      matched_logs: lambdaResponse.matched_logs || 0,
      detected_threats: lambdaResponse.detected_threats || [],
      execution_time_ms: lambdaResponse.execution_time_ms || 0,
    });

  } catch (error) {
    console.error('Error in test-run endpoint:', error);
    return NextResponse.json({
      success: false,
      rule_id: 'unknown',
      total_logs: 0,
      matched_logs: 0,
      detected_threats: [],
      execution_time_ms: 0,
      error_message: `Internal server error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    }, { status: 500 });
  }
}

/**
 * Call validation handler Lambda function
 * This invokes the backend Lambda that implements rule testing logic
 */
async function callValidationHandler(payload: any): Promise<any> {
  try {
    // In production, this would invoke an AWS Lambda function
    // For now, we'll simulate the response based on the payload
    const startTime = Date.now();

    // Simulate rule evaluation based on rule_type
    const rule = payload.rule;
    const testLogs = payload.test_logs;

    let matchedLogs = 0;
    const detectedThreats: any[] = [];

    if (rule.rule_type === 'connection_spike') {
      matchedLogs = testLogs.filter((log: any) => log.event_type === '$connect').length;
    } else if (rule.rule_type === 'auth_failure') {
      matchedLogs = testLogs.filter(
        (log: any) => log.event_type?.includes('auth') && log.status?.includes('fail')
      ).length;
    } else if (rule.rule_type === 'unknown_region') {
      const allowedRegions = rule.condition?.allowed_regions || [];
      matchedLogs = testLogs.filter(
        (log: any) => log.region && !allowedRegions.includes(log.region)
      ).length;
    } else if (rule.rule_type === 'public_bucket') {
      matchedLogs = testLogs.filter(
        (log: any) => log.service === 's3' && log.event_type?.includes('bucket')
      ).length;
    }

    // Generate threats if matches found
    if (matchedLogs > 0) {
      detectedThreats.push({
        threat_id: `threat-${Math.random().toString(36).substr(2, 9)}`,
        rule_id: rule.rule_id || 'test-rule',
        severity: rule.priority || 5,
        account_id: payload.account_id || 'test-account',
        timestamp: new Date().toISOString(),
        message: `Rule '${rule.rule_type}' triggered by ${matchedLogs} event(s)`,
        evidence_count: matchedLogs,
      });
    }

    const executionTime = Date.now() - startTime;

    return {
      success: true,
      matched_logs: matchedLogs,
      detected_threats: detectedThreats,
      execution_time_ms: executionTime,
    };

  } catch (error) {
    console.error('Error calling validation handler:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
