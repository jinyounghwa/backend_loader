'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuditLogs } from '@/lib/hooks/useAuditLogs';
import { useAuditLogStream } from '@/lib/hooks/useAuditLogStream';
import { AuditLogsFilter } from './AuditLogsFilter';
import { AuditLogsTimeline } from './AuditLogsTimeline';
import { ChevronLeft, ChevronRight, Radio } from 'lucide-react';

interface AuditLogsDashboardProps {
  connectionId?: string;
}

interface Account {
  id: string;
  name: string;
}

export function AuditLogsDashboard({ connectionId }: AuditLogsDashboardProps) {
  const [filters, setFilters] = useState<{
    accountId?: string;
    startTime: string;
    endTime: string;
    eventType: string;
    offset: number;
    limit: number;
  }>({
    accountId: undefined,
    startTime: '',
    endTime: '',
    eventType: '',
    offset: 0,
    limit: 50,
  });

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [streamConnected, setStreamConnected] = useState(false);

  // 계정 목록 로드
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const res = await fetch('/api/guardian/accounts');
        const data = await res.json();
        setAccounts(data.accounts || []);
      } catch (error) {
        console.error('Failed to fetch accounts:', error);
        setAccounts([]);
      } finally {
        setLoadingAccounts(false);
      }
    };

    fetchAccounts();
  }, []);

  // 실시간 스트림 이벤트 핸들러
  const handleNewLog = useCallback(() => {
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('auditLogAdded'));
    }, 100);
  }, []);

  const { logs, total, hasMore, isLoading } = useAuditLogs({
    accountId: filters.accountId,
    connectionId: connectionId || undefined,
    startTime: filters.startTime,
    endTime: filters.endTime,
    eventType: filters.eventType,
    limit: filters.limit,
    offset: filters.offset,
  });

  // 실시간 스트림 연결
  const { isConnected } = useAuditLogStream({
    accountId: filters.accountId,
    connectionId: connectionId,
    onNewLog: handleNewLog,
    onError: (error) => {
      console.error('Stream error:', error);
      setStreamConnected(false);
    },
  });

  useEffect(() => {
    setStreamConnected(isConnected);
  }, [isConnected]);

  const currentPage = Math.floor(filters.offset / filters.limit) + 1;
  const totalPages = Math.ceil(total / filters.limit);
  const startIdx = filters.offset + 1;
  const endIdx = Math.min(filters.offset + filters.limit, total);

  const handlePrevious = () => {
    setFilters((prev) => ({
      ...prev,
      offset: Math.max(0, prev.offset - prev.limit),
    }));
  };

  const handleNext = () => {
    setFilters((prev) => ({
      ...prev,
      offset: prev.offset + prev.limit,
    }));
  };

  const handleLimitChange = (newLimit: number) => {
    setFilters((prev) => ({
      ...prev,
      limit: newLimit,
      offset: 0,
    }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-white">감시 로그</h2>
          <div className="flex items-center gap-1">
            <Radio
              className={`w-4 h-4 ${streamConnected ? 'fill-green-500 text-green-500' : 'text-gray-500'}`}
            />
            <span className="text-xs text-gray-400">
              {streamConnected ? '실시간 연결' : '폴링 모드'}
            </span>
          </div>
        </div>
        <div className="text-sm text-gray-400">
          총 <span className="font-bold text-white">{total}</span>건
        </div>
      </div>

      {/* 필터 섹션 */}
      <AuditLogsFilter value={filters} onChange={setFilters} accounts={accounts} />

      {/* 타임라인 섹션 */}
      <AuditLogsTimeline logs={logs} isLoading={isLoading} />

      {/* 페이지네이션 */}
      <div className="flex items-center justify-between p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-sm text-gray-400">
          {total === 0 ? (
            <span>검색 결과 없음</span>
          ) : (
            <span>
              {startIdx} ~ {endIdx} / {total}건
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevious}
            disabled={filters.offset === 0 || isLoading}
            className="flex items-center gap-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden sm:inline">이전</span>
          </button>

          <div className="text-sm text-gray-400 min-w-24 text-center">
            {total === 0 ? '-' : `${currentPage} / ${totalPages}`}
          </div>

          <button
            onClick={handleNext}
            disabled={!hasMore || isLoading}
            className="flex items-center gap-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            <span className="hidden sm:inline">다음</span>
            <ChevronRight className="w-4 h-4" />
          </button>

          <div className="w-px h-6 bg-slate-600 mx-2" />

          <select
            value={filters.limit}
            onChange={(e) => handleLimitChange(parseInt(e.target.value))}
            className="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="10">10개</option>
            <option value="25">25개</option>
            <option value="50">50개</option>
            <option value="100">100개</option>
            <option value="200">200개</option>
          </select>
        </div>
      </div>

      {/* 새로고침 정보 */}
      <div className="text-xs text-gray-500 text-center">
        {streamConnected
          ? '실시간 이벤트 수신 중 (폴링: 30초)'
          : '자동 새로고침: 30초 주기'}
      </div>
    </div>
  );
}
