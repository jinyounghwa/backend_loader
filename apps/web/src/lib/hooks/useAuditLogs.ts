import useSWR from 'swr';
import { AuditLog, AuditLogsResponse } from '@/app/api/guardian/audit-logs/route';

interface UseAuditLogsOptions {
  accountId?: string;
  connectionId?: string;
  startTime?: string;
  endTime?: string;
  eventType?: string;
  limit?: number;
  offset?: number;
}

interface UseAuditLogsReturn {
  logs: AuditLog[];
  total: number;
  hasMore: boolean;
  isLoading: boolean;
  error?: Error;
  mutate: () => void;
}

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useAuditLogs(options?: UseAuditLogsOptions): UseAuditLogsReturn {
  const limit = options?.limit ?? 50;
  const offset = options?.offset ?? 0;

  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

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
  if (options?.eventType) {
    params.append('event_type', options.eventType);
  }

  const url = `/api/guardian/audit-logs?${params.toString()}`;

  const { data, error, mutate } = useSWR<AuditLogsResponse>(url, fetcher, {
    refreshInterval: 30_000, // 30초 자동 새로고침 (실시간 스트림 보조)
    dedupingInterval: 10_000, // 10초 내 중복 요청 제거
    focusThrottleInterval: 300_000, // 5분
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    errorRetryCount: 3,
    errorRetryInterval: 5_000,
  });

  return {
    logs: data?.items ?? [],
    total: data?.total ?? 0,
    hasMore: data?.hasMore ?? false,
    isLoading: !error && !data,
    error,
    mutate,
  };
}
