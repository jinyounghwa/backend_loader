import { getAuthSession } from '@/lib/auth-utils';
import { NextResponse } from 'next/server';

export interface Account {
  id: string;
  name: string;
}

export interface AccountsResponse {
  accounts: Account[];
}

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const apiEndpoint = process.env.AUDIT_API_ENDPOINT;
    if (!apiEndpoint) {
      console.error('AUDIT_API_ENDPOINT not configured');
      return NextResponse.json(
        { error: 'API endpoint not configured' },
        { status: 500 }
      );
    }

    // Call backend API to get accounts list
    const accountsUrl = new URL('/accounts', apiEndpoint).toString();
    const response = await fetch(accountsUrl);

    if (!response.ok) {
      console.error(`Failed to fetch accounts: ${response.status}`);
      // Return empty list on error to avoid breaking the UI
      return NextResponse.json(
        { accounts: [] },
        { status: 200 }
      );
    }

    const data = await response.json();
    const accounts: Account[] = data.accounts || [];

    return NextResponse.json(
      { accounts },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error fetching accounts:', error);
    return NextResponse.json(
      { error: 'Failed to fetch accounts' },
      { status: 500 }
    );
  }
}
