import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export interface RemediationRequest {
  threat_id: string;
  threat_type: 'public_bucket' | 'unauthorized_region' | 'high_cost';
  resource_id: string;
  auto_remediate: boolean;
}

export interface RemediationResult {
  success: boolean;
  threat_id: string;
  action: string;
  status: 'completed' | 'pending' | 'failed';
  details: Record<string, any>;
  timestamp: string;
}

export async function POST(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const body: RemediationRequest = await request.json();

    if (!body.auto_remediate) {
      // 수동 검토 필요
      return NextResponse.json({
        success: true,
        threat_id: body.threat_id,
        action: 'require_approval',
        status: 'pending',
        details: {
          message: 'This threat requires manual approval',
          assigned_to: 'security_team',
        },
        timestamp: new Date().toISOString(),
      } as RemediationResult);
    }

    // 자동 치료 실행
    let action = '';
    const details: Record<string, any> = {};

    switch (body.threat_type) {
      case 'public_bucket':
        action = 'block_s3_public_access';
        details.bucket_name = body.resource_id;
        details.remediation = 'S3 public access block applied';
        break;

      case 'unauthorized_region':
        action = 'stop_ec2_instance';
        details.instance_id = body.resource_id;
        details.remediation = 'EC2 instance stopped';
        break;

      case 'high_cost':
        action = 'alert_admin';
        details.message = 'Admin alert sent for cost review';
        break;

      default:
        return NextResponse.json(
          { error: 'Unknown threat type' },
          { status: 400 }
        );
    }

    // 시뮬레이션: 실제 AWS API 호출
    const result: RemediationResult = {
      success: true,
      threat_id: body.threat_id,
      action,
      status: 'completed',
      details: {
        ...details,
        applied_at: new Date().toISOString(),
        remediation_logs: [
          `Threat ${body.threat_id} detected`,
          `Executing: ${action}`,
          `Resource: ${body.resource_id}`,
          'Remediation completed successfully',
        ],
      },
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to execute remediation' },
      { status: 500 }
    );
  }
}
