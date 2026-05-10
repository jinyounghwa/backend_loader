import { NextResponse } from 'next/server';
import { getAuthSession } from '@/lib/auth-utils';
import { getLatestCheckResult, getRecentEvents, ddbItemToGuardianEvent } from '@/lib/dynamodb';
import { mockCostData, mockEC2Data, mockS3Data, mockEvents } from '@/lib/mock-data';
import { statusCache } from '@/lib/cache';
import type { DashboardSummary, DynamoEventItem, GuardianEvent, MultiRegionSummary } from '@/types/guardian';

export const dynamic = 'force-dynamic';
const CHECK_INTERVAL_MINUTES = 60;
const STALE_THRESHOLD_MINUTES = 65;

function generateNextCheckTime(): string {
  return new Date(Date.now() + CHECK_INTERVAL_MINUTES * 60 * 1000).toISOString();
}

function isStaleData(lastCheckTime: string): boolean {
  const lastCheckMs = new Date(lastCheckTime).getTime();
  const ageMinutes = (Date.now() - lastCheckMs) / (1000 * 60);
  return ageMinutes > STALE_THRESHOLD_MINUTES;
}

function buildFallbackSummary(region: string = 'ap-northeast-1'): DashboardSummary {
  return {
    cost: mockCostData,
    ec2: mockEC2Data,
    s3: mockS3Data,
    recent_events: mockEvents.slice(0, 5),
    last_check: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    next_check: generateNextCheckTime(),
    system_health: 'warning',
    region,
    is_stale: false,
  };
}



function extractCheckDetails(rawDetails: Record<string, any>) {
  const costRaw = rawDetails.cost;
  const ec2Raw = rawDetails.ec2;
  const s3Raw = rawDetails.s3;

  const costData = costRaw?.details ?? costRaw ?? mockCostData;
  const ec2Data = ec2Raw?.details ?? ec2Raw ?? mockEC2Data;
  const s3Data = s3Raw?.details ?? s3Raw ?? mockS3Data;

  const normalizedCost = {
    today_cost: costData.today_cost ?? 0,
    yesterday_cost: costData.yesterday_cost ?? 0,
    monthly_cost: costData.monthly_cost ?? 0,
    increase_percent: costData.increase_percent ?? 0,
    threshold: costData.threshold ?? 10,
    is_anomaly: costData.is_anomaly ?? false,
    date: costData.date ?? new Date().toISOString().split('T')[0],
    daily_costs: costData.daily_costs ?? mockCostData.daily_costs,
  };

  const newInstances = ec2Data.new_instances ?? [];
  const ec2Anomalies: Array<{
    type: 'unauthorized_region' | 'open_port' | 'new_instance';
    instance_id: string;
    region: string;
    details: string;
    severity: 'critical' | 'warning' | 'info';
  }> = [];
  for (const inst of newInstances) {
    ec2Anomalies.push({
      type: 'new_instance',
      instance_id: inst.instance_id,
      region: inst.region,
      details: `New instance ${inst.instance_id} (${inst.instance_type}) launched`,
      severity: 'warning',
    });
  }
  for (const exp of (ec2Data.exposed_instances ?? [])) {
    ec2Anomalies.push({
      type: 'open_port',
      instance_id: exp.instance_id,
      region: exp.region,
      details: `Exposed security group on ${exp.instance_id}`,
      severity: 'critical',
    });
  }
  const normalizedEC2 = {
    total_instances: ec2Data.total_instances ?? newInstances.length,
    running_instances: ec2Data.running_instances ?? newInstances.length,
    stopped_instances: ec2Data.stopped_instances ?? 0,
    anomalies: ec2Anomalies,
    exposed_instances: ec2Data.exposed_instances ?? [],
    instances_by_region: ec2Data.instances_by_region ?? {},
  };

  const publicBuckets: Array<{ bucket_name: string; public_reasons: string[]; created: string }> = [];
  for (const b of (s3Data.public_buckets ?? [])) {
    publicBuckets.push({
      bucket_name: b.bucket_name ?? b.BucketName ?? '',
      public_reasons: b.public_reasons ?? [],
      created: b.creation_date ?? b.created ?? '',
    });
  }
  const newBuckets: Array<{ bucket_name: string; created: string }> = [];
  for (const b of (s3Data.new_buckets ?? [])) {
    newBuckets.push({
      bucket_name: b.bucket_name ?? b.BucketName ?? '',
      created: b.creation_date ?? b.created ?? '',
    });
  }
  const s3Anomalies: Array<{
    type: 'public_bucket' | 'new_bucket';
    bucket_name: string;
    details: string;
    severity: 'critical' | 'warning' | 'info';
  }> = [];
  for (const b of publicBuckets) {
    s3Anomalies.push({
      type: 'public_bucket',
      bucket_name: b.bucket_name,
      details: `Public bucket: ${b.bucket_name} (${b.public_reasons.join(', ')})`,
      severity: 'critical',
    });
  }
  for (const b of newBuckets) {
    s3Anomalies.push({
      type: 'new_bucket',
      bucket_name: b.bucket_name,
      details: `New bucket: ${b.bucket_name}`,
      severity: 'info',
    });
  }
  const normalizedS3 = {
    total_buckets: s3Data.total_buckets ?? (publicBuckets.length + newBuckets.length),
    public_buckets: publicBuckets,
    new_buckets: newBuckets,
    anomalies: s3Anomalies,
  };

  return {
    cost: normalizedCost,
    ec2: normalizedEC2,
    s3: normalizedS3,
    last_check: rawDetails.last_check,
    system_health: rawDetails.system_health ?? 'healthy',
  };
}

async function fetchRegionData(region: string, useCache: boolean = true): Promise<DashboardSummary | null> {
  const cacheKey = `status_${region}`;

  if (useCache) {
    const cached = statusCache.get<DashboardSummary>(cacheKey);
    if (cached) {
      return cached;
    }
  }

  try {
    const [checkResult, rawEvents] = await Promise.all([
      getLatestCheckResult(),
      getRecentEvents(24),
    ]);

    if (!checkResult) {
      return null;
    }

    const rawDetails: Record<string, any> = typeof checkResult.details === 'string'
      ? JSON.parse(checkResult.details)
      : checkResult.details;

    const details = extractCheckDetails(rawDetails);

    const recent_events = rawEvents.map((item, i) =>
      ddbItemToGuardianEvent(item as unknown as DynamoEventItem, i)
    );

    const summary: DashboardSummary = {
      cost: details.cost,
      ec2: details.ec2,
      s3: details.s3,
      recent_events: recent_events.slice(0, 5),
      last_check: details.last_check,
      next_check: generateNextCheckTime(),
      system_health: details.system_health,
      region,
      is_stale: isStaleData(details.last_check),
    };

    statusCache.set(cacheKey, summary);
    return summary;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const session = await getAuthSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { searchParams } = new URL(request.url);
    const regionsParam = searchParams.get('regions');
    const cacheParam = searchParams.get('cache');
    const useCache = cacheParam !== 'false'; // Default to using cache unless explicitly disabled
    const regions = regionsParam
      ? regionsParam.split(',').filter(r => r.trim())
      : ['ap-northeast-1'];

    if (regions.length === 1) {
      const region = regions[0];
      const data = await fetchRegionData(region, useCache);
      const response = NextResponse.json(data || buildFallbackSummary(region));

      // Set cache-control header (5 minutes for browsers)
      response.headers.set('cache-control', useCache ? 'private, max-age=300' : 'no-cache, no-store');
      return response;
    }

    const results = await Promise.allSettled(
      regions.map(region => fetchRegionData(region, useCache))
    );

    const summaries: DashboardSummary[] = [];
    const errors: Record<string, string> = {};

    results.forEach((result, index) => {
      const region = regions[index];
      if (result.status === 'fulfilled' && result.value) {
        summaries.push(result.value);
      } else if (result.status === 'rejected') {
        errors[region] = 'Failed to fetch region data';
        summaries.push(buildFallbackSummary(region));
      } else {
        summaries.push(buildFallbackSummary(region));
      }
    });

    const multiRegionSummary: MultiRegionSummary = {
      regions: summaries,
      last_check: new Date().toISOString(),
      errors,
    };

    const response = NextResponse.json(multiRegionSummary);
    response.headers.set('cache-control', useCache ? 'private, max-age=300' : 'no-cache, no-store');
    return response;
  } catch {
    return NextResponse.json(buildFallbackSummary());
  }
}
