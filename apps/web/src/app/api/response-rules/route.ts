import { NextResponse } from 'next/server';
import { auth } from '@auth';

interface ResponseRule {
  rule_id: string;
  region: string;
  event_type: string;
  action: string;
  enabled: boolean;
  priority: number;
  dry_run: boolean;
  created_at: string;
  created_by?: string;
}

// Mock rules data
const mockRules: ResponseRule[] = [
  {
    rule_id: 'rule-001',
    region: 'ap-northeast-1',
    event_type: 'unauthorized_region',
    action: 'stop_instance',
    enabled: true,
    priority: 10,
    dry_run: false,
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    created_by: 'admin@example.com',
  },
  {
    rule_id: 'rule-002',
    region: 'us-east-1',
    event_type: 'open_port',
    action: 'stop_instance',
    enabled: true,
    priority: 20,
    dry_run: false,
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    created_by: 'admin@example.com',
  },
  {
    rule_id: 'rule-003',
    region: '*',
    event_type: 'public_bucket',
    action: 'block_bucket',
    enabled: true,
    priority: 15,
    dry_run: false,
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    created_by: 'admin@example.com',
  },
];

function isAdmin(session: any): boolean {
  return session?.user?.email === 'timotolkie@gmail.com';
}

export async function GET(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const region = searchParams.get('region');

    let rules = mockRules;

    // Filter by region if provided
    if (region) {
      rules = rules.filter(r => r.region === region || r.region === '*');
      rules.sort((a, b) => a.priority - b.priority);
    }

    return NextResponse.json({
      rules,
      total: rules.length,
      timestamp: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json(
      { error: 'Failed to fetch rules' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session || !isAdmin(session)) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  try {
    const rule = await request.json();

    // Validate rule
    if (!rule.rule_id || !rule.region || !rule.event_type || !rule.action) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // In production, save to DynamoDB via Python Lambda
    // For now, just validate and return success
    const newRule: ResponseRule = {
      ...rule,
      enabled: rule.enabled ?? true,
      priority: rule.priority ?? 100,
      dry_run: rule.dry_run ?? false,
      created_at: rule.created_at || new Date().toISOString(),
      created_by: session.user?.email,
    };

    return NextResponse.json(
      { success: true, rule: newRule },
      { status: 201 }
    );
  } catch {
    return NextResponse.json(
      { error: 'Failed to create rule' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: Request) {
  const session = await auth();
  if (!session || !isAdmin(session)) {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const ruleId = searchParams.get('rule_id');

    if (!ruleId) {
      return NextResponse.json(
        { error: 'Missing rule_id parameter' },
        { status: 400 }
      );
    }

    // In production, delete from DynamoDB via Python Lambda
    return NextResponse.json({ success: true, deleted_id: ruleId });
  } catch {
    return NextResponse.json(
      { error: 'Failed to delete rule' },
      { status: 500 }
    );
  }
}
