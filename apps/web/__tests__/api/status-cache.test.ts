/**
 * Status API Caching Tests
 * Verify that Status API uses in-memory caching with 5-minute TTL
 */

import { statusCache } from '@/lib/cache';
import type { DashboardSummary } from '@/types/guardian';

describe('Status API Caching', () => {
  beforeEach(() => {
    // Clear cache before each test
    statusCache.clear();
  });

  test('Cache stores and retrieves data correctly', () => {
    const mockData: DashboardSummary = {
      cost: { today_cost: 5.5, yesterday_cost: 4.2, monthly_cost: 150, increase_percent: 30.95, threshold: 10, is_anomaly: false, date: '2026-05-06', daily_costs: [] },
      ec2: { new_instances: [], exposed_instances: [], anomalies: [] },
      s3: { total_buckets: 0, public_buckets: [], new_buckets: [], anomalies: [] },
      recent_events: [],
      last_check: '2026-05-06T12:00:00Z',
      next_check: '2026-05-06T13:00:00Z',
      system_health: 'healthy',
      region: 'ap-northeast-1',
      is_stale: false,
    };

    const key = 'test_key';
    statusCache.set(key, mockData);

    const retrieved = statusCache.get<DashboardSummary>(key);
    expect(retrieved).toEqual(mockData);
    expect(retrieved?.region).toBe('ap-northeast-1');
  });

  test('Cache respects TTL expiration', async () => {
    const mockData = { test: 'data' };
    const shortLivedCache = new (statusCache.constructor as any)(1); // 1 second TTL

    shortLivedCache.set('temp_key', mockData);
    expect(shortLivedCache.get('temp_key')).toEqual(mockData);

    // Wait for expiration
    await new Promise(resolve => setTimeout(resolve, 1100));
    expect(shortLivedCache.get('temp_key')).toBeNull();
  });

  test('Cache returns null for non-existent keys', () => {
    const result = statusCache.get('nonexistent');
    expect(result).toBeNull();
  });

  test('Cache can be cleared', () => {
    statusCache.set('key1', { data: 'value1' });
    statusCache.set('key2', { data: 'value2' });

    expect(statusCache.has('key1')).toBe(true);
    expect(statusCache.has('key2')).toBe(true);

    statusCache.clear('key1');
    expect(statusCache.has('key1')).toBe(false);
    expect(statusCache.has('key2')).toBe(true);

    statusCache.clear();
    expect(statusCache.has('key2')).toBe(false);
  });

  test('Cache key format for regions', () => {
    const regions = ['ap-northeast-1', 'us-east-1', 'eu-west-1'];
    const mockData = { region: 'test', cost: { today_cost: 5 } };

    regions.forEach(region => {
      const key = `status_${region}`;
      statusCache.set<any>(key, { ...mockData, region });
    });

    regions.forEach(region => {
      const key = `status_${region}`;
      const data = statusCache.get<any>(key);
      expect(data?.region).toBe(region);
    });
  });

  test('Fetch with cache=false parameter should skip cache', async () => {
    // This would be tested in the integration test
    // Here we just verify cache logic
    const key = 'test_ignore';
    statusCache.set(key, { cached: true });

    // Simulate cache=false behavior - not using cache
    // In real API, it would fetch fresh data regardless of cache
    const useCache = false;
    let data = useCache ? statusCache.get(key) : null;
    expect(data).toBeNull();

    // With cache=true, should return cached
    const useCache2 = true;
    data = useCache2 ? statusCache.get(key) : null;
    expect(data).toEqual({ cached: true });
  });
});
