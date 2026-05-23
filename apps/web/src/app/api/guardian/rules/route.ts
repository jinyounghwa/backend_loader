'use server';

import { NextRequest, NextResponse } from 'next/server';

interface SecurityRule {
  rule_id: string;
  rule_type: string;
  condition: Record<string, any>;
  action: Record<string, any>;
  priority: number;
  account_id?: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface RulesResponse {
  rules?: SecurityRule[];
  rule?: SecurityRule;
  error?: string;
  count?: number;
}

async function callRulesAPI(
  method: string,
  path: string,
  body?: any
): Promise<any> {
  const apiEndpoint = process.env.AUDIT_API_ENDPOINT;
  if (!apiEndpoint) {
    throw new Error('AUDIT_API_ENDPOINT not configured');
  }

  const url = `${apiEndpoint}${path}`;
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || `API error: ${response.status}`);
  }

  return data;
}

export async function GET(request: NextRequest): Promise<NextResponse<RulesResponse>> {
  try {
    const { searchParams } = new URL(request.url);
    const ruleType = searchParams.get('rule_type');
    const accountId = searchParams.get('account_id');
    const ruleId = searchParams.get('rule_id');

    let path = '/rules';
    if (ruleId) {
      path += `/${ruleId}`;
    } else {
      const params = new URLSearchParams();
      if (ruleType) params.append('rule_type', ruleType);
      if (accountId) params.append('account_id', accountId);
      if (params.toString()) {
        path += `?${params.toString()}`;
      }
    }

    const data = await callRulesAPI('GET', path);
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch rules';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest): Promise<NextResponse<RulesResponse>> {
  try {
    const body = await request.json();

    // Validate required fields
    const required = ['rule_type', 'condition', 'action', 'priority'];
    for (const field of required) {
      if (!(field in body)) {
        return NextResponse.json(
          { error: `Missing required field: ${field}` },
          { status: 400 }
        );
      }
    }

    const data = await callRulesAPI('POST', '/rules', body);
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create rule';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest): Promise<NextResponse<RulesResponse>> {
  try {
    const { searchParams } = new URL(request.url);
    const ruleId = searchParams.get('rule_id');

    if (!ruleId) {
      return NextResponse.json({ error: 'Missing rule_id' }, { status: 400 });
    }

    const body = await request.json();
    const data = await callRulesAPI('PUT', `/rules/${ruleId}`, body);
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to update rule';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest): Promise<NextResponse<RulesResponse>> {
  try {
    const { searchParams } = new URL(request.url);
    const ruleId = searchParams.get('rule_id');

    if (!ruleId) {
      return NextResponse.json({ error: 'Missing rule_id' }, { status: 400 });
    }

    await callRulesAPI('DELETE', `/rules/${ruleId}`);
    return NextResponse.json({});
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to delete rule';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
