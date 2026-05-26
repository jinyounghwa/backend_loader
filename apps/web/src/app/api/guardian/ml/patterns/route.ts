import { NextRequest, NextResponse } from 'next/server';
import { invokeLambda } from '@/lib/aws/lambda-client';

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json();

    const { threats, min_support = 0.3 } = body;

    if (!threats || !Array.isArray(threats)) {
      return NextResponse.json(
        { error: 'threats array is required' },
        { status: 400 }
      );
    }

    const lambdaResponse = await invokeLambda('ml_patterns', {
      threats,
      min_support
    });

    const result = JSON.parse(lambdaResponse.body);

    return NextResponse.json(result, {
      status: lambdaResponse.statusCode || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Identify patterns error:', error);
    return NextResponse.json(
      { error: 'Failed to identify patterns' },
      { status: 500 }
    );
  }
};
