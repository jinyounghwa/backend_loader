import { getAuthSession } from '@/lib/auth-utils';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const session = await getAuthSession();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const searchParams = request.nextUrl.searchParams;
    const format = searchParams.get('format') || 'json'; // json, csv
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');

    // Mock 이벤트 데이터
    const events = [
      {
        id: 'evt-001',
        timestamp: new Date(Date.now() - 86400000).toISOString(),
        severity: 'HIGH',
        check_type: 'cost',
        title: 'Cost Threshold Exceeded',
        message: 'Daily cost $20.00 exceeds threshold $10.00',
      },
      {
        id: 'evt-002',
        timestamp: new Date(Date.now() - 172800000).toISOString(),
        severity: 'MEDIUM',
        check_type: 'ec2',
        title: 'Unauthorized Region EC2',
        message: 'EC2 instance detected in unauthorized region',
      },
      {
        id: 'evt-003',
        timestamp: new Date(Date.now() - 259200000).toISOString(),
        severity: 'HIGH',
        check_type: 's3',
        title: 'Public Bucket Detected',
        message: 'S3 bucket with public access detected',
      },
    ];

    if (format === 'csv') {
      // CSV 포맷으로 변환
      const header = ['ID', 'Timestamp', 'Severity', 'Check Type', 'Title', 'Message'];
      const rows = events.map((e) => [
        e.id,
        e.timestamp,
        e.severity,
        e.check_type,
        e.title,
        e.message,
      ]);

      const csv = [
        header.join(','),
        ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
      ].join('\n');

      return new Response(csv, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="events-report.csv"',
        },
      });
    }

    // JSON 포맷 (기본)
    return NextResponse.json({
      events,
      total: events.length,
      period: {
        startDate: startDate || 'N/A',
        endDate: endDate || 'N/A',
      },
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to generate report' },
      { status: 500 }
    );
  }
}
