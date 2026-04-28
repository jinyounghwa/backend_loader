'use client';

import useSWR from 'swr';
import type { DashboardSummary, GuardianEvent } from '@/types/guardian';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useDashboard() {
  const { data, error, isLoading, mutate } = useSWR<DashboardSummary>(
    '/api/status',
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: true }
  );

  return {
    summary: data,
    isLoading,
    isError: !!error,
    refresh: mutate,
  };
}

export function useEvents(
  typeFilter?: string,
  severityFilter?: string,
  startDate?: string,
  endDate?: string
) {
  const params = new URLSearchParams();
  if (typeFilter && typeFilter !== 'all') params.set('type', typeFilter);
  if (severityFilter && severityFilter !== 'all') params.set('severity', severityFilter);
  if (startDate) params.set('startDate', startDate);
  if (endDate) params.set('endDate', endDate);
  const qs = params.toString();
  const url = `/api/events${qs ? `?${qs}` : ''}`;

  const { data, error, isLoading, mutate } = useSWR<{ events: GuardianEvent[]; total: number }>(
    url,
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: true }
  );

  return {
    events: data?.events ?? [],
    total: data?.total ?? 0,
    isLoading,
    isError: !!error,
    refresh: mutate,
  };
}
