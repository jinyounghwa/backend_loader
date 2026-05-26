import { NextRequest, NextResponse } from 'next/server';
import { invokeLambda } from '@/lib/aws/lambda-client';

export const GET = async (request: NextRequest) => {
  try {
    const { searchParams } = new URL(request.url);
    const account_id = searchParams.get('account_id');
    const time_range = searchParams.get('time_range') || '24h';

    if (!account_id) {
      return NextResponse.json(
        { error: 'account_id is required' },
        { status: 400 }
      );
    }

    const lambdaResponse = await invokeLambda('ml_trends', {
      account_id,
      time_range
    });

    const result = JSON.parse(lambdaResponse.body);

    return NextResponse.json(result, {
      status: lambdaResponse.statusCode || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Analyze trends error:', error);
    return NextResponse.json(
      { error: 'Failed to analyze trends' },
      { status: 500 }
    );
  }
};
