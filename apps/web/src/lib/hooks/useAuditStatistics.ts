'use client';

import useSWR from 'swr';
import { AuditStatistics } from '@/app/api/guardian/audit-logs/statistics/route';

interface UseAuditStatisticsOptions {
  accountId?: string;
  connectionId?: string;
  startTime?: string;
  endTime?: string;
}

interface UseAuditStatisticsReturn {
  statistics: AuditStatistics | null;
  isLoading: boolean;
  error?: Error;
  mutate: () => void;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useAuditStatistics(
  options?: UseAuditStatisticsOptions
): UseAuditStatisticsReturn {
  const params = new URLSearchParams();

  if (options?.accountId) {
    params.append('account_id', options.accountId);
  }
  if (options?.connectionId) {
    params.append('connection_id', options.connectionId);
  }
  if (options?.startTime) {
    params.append('start_time', options.startTime);
  }
  if (options?.endTime) {
    params.append('end_time', options.endTime);
  }

  const url = `/api/guardian/audit-logs/statistics?${params.toString()}`;

  const { data, error, mutate } = useSWR<AuditStatistics>(url, fetcher, {
    refreshInterval: 60_000, // 60초 새로고침
    dedupingInterval: 10_000,
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    errorRetryCount: 3,
    errorRetryInterval: 5_000,
  });

  return {
    statistics: data || null,
    isLoading: !error && !data,
    error,
    mutate,
  };
}
