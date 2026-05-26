import { NextRequest, NextResponse } from 'next/server';
import { invokeLambda } from '@/lib/aws/lambda-client';

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json();

    const { account_id, days_ahead = 7 } = body;

    if (!account_id) {
      return NextResponse.json(
        { error: 'account_id is required' },
        { status: 400 }
      );
    }

    const lambdaResponse = await invokeLambda('ml_predict', {
      account_id,
      days_ahead
    });

    const result = JSON.parse(lambdaResponse.body);

    return NextResponse.json(result, {
      status: lambdaResponse.statusCode || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Predict threats error:', error);
    return NextResponse.json(
      { error: 'Failed to predict threats' },
      { status: 500 }
    );
  }
};
