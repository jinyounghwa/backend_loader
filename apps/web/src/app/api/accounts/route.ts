import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export async function GET() {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const accounts = [
      {
        account_id: '123456789012',
        account_name: 'Production',
        account_email: 'aws-prod@example.com',
        arn: 'arn:aws:iam::123456789012:root',
        status: 'Active' as const,
        joined_date: '2024-01-01',
      },
      {
        account_id: '210987654321',
        account_name: 'Development',
        account_email: 'aws-dev@example.com',
        arn: 'arn:aws:iam::210987654321:root',
        status: 'Active' as const,
        joined_date: '2024-01-15',
      },
      {
        account_id: '345678901234',
        account_name: 'Staging',
        account_email: 'aws-staging@example.com',
        arn: 'arn:aws:iam::345678901234:root',
        status: 'Active' as const,
        joined_date: '2024-02-01',
      },
    ];

    return NextResponse.json({ accounts });
  } catch (error) {
    console.error('Failed to fetch accounts:', error);
    return NextResponse.json({ error: 'Failed to fetch accounts' }, { status: 500 });
  }
}
