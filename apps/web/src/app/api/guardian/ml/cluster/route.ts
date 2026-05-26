import { NextRequest, NextResponse } from 'next/server';
import { invokeLambda } from '@/lib/aws/lambda-client';

export const POST = async (request: NextRequest) => {
  try {
    const body = await request.json();

    const { threats, n_clusters = 5 } = body;

    if (!threats || !Array.isArray(threats)) {
      return NextResponse.json(
        { error: 'threats array is required' },
        { status: 400 }
      );
    }

    const lambdaResponse = await invokeLambda('ml_cluster', {
      threats,
      n_clusters
    });

    const result = JSON.parse(lambdaResponse.body);

    return NextResponse.json(result, {
      status: lambdaResponse.statusCode || 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Cluster threats error:', error);
    return NextResponse.json(
      { error: 'Failed to cluster threats' },
      { status: 500 }
    );
  }
};
