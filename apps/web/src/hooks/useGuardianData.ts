'use client';

import useSWR from 'swr';
import type { DashboardSummary, GuardianEvent } from '@/types/guardian';

const fetcher = (url: string) => fetch(url).then(res => res.json());

const defaultOptions = {
  dedupingInterval: 60_000,
  focusThrottleInterval: 300_000,
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  shouldRetryOnError: true,
};

export function useDashboard(regions?: string[]) {
  const regionsParam = regions && regions.length > 0
    ? `?regions=${regions.join(',')}`
    : '';
  const url = `/api/status${regionsParam}`;

  const { data, error, isLoading, mutate } = useSWR<DashboardSummary | any>(
    url,
    fetcher,
    { ...defaultOptions, refreshInterval: 60_000 }
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
    { ...defaultOptions, refreshInterval: 60_000 }
  );

  return {
    events: data?.events ?? [],
    total: data?.total ?? 0,
    isLoading,
    isError: !!error,
    refresh: mutate,
  };
}
