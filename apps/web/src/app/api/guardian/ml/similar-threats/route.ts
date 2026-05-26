import { NextRequest, NextResponse } from 'next/server';
import { invokeLambda } from '@/lib/aws/lambda-client';

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json();

    const { threat_id, all_threats, similarity_threshold = 0.7 } = body;

    if (!threat_id || !all_threats || !Array.isArray(all_threats)) {
      return NextResponse.json(
        { error: 'threat_id and all_threats array are required' },
        { status: 400 }
      );
    }

    const lambdaResponse = await invokeLambda('ml_similar', {
      threat_id,
      all_threats,
      similarity_threshold
    });

    const result = JSON.parse(lambdaResponse.body);

    return NextResponse.json(result, {
      status: lambdaResponse.statusCode || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Get similar threats error:', error);
    return NextResponse.json(
      { error: 'Failed to get similar threats' },
      { status: 500 }
    );
  }
};
