'use client';

import { useState } from 'react';
import { useAuditLogs } from '@/lib/hooks/useAuditLogs';
import { AuditLogsFilter } from './AuditLogsFilter';
import { AuditLogsTimeline } from './AuditLogsTimeline';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface AuditLogsDashboardProps {
  connectionId?: string;
}

export function AuditLogsDashboard({ connectionId = 'all' }: AuditLogsDashboardProps) {
  const [filters, setFilters] = useState({
    startTime: '',
    endTime: '',
    eventType: '',
    offset: 0,
    limit: 50,
  });

  const { logs, total, hasMore, isLoading } = useAuditLogs(connectionId, filters);

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
        <h2 className="text-2xl font-bold text-white">감시 로그</h2>
        <div className="text-sm text-gray-400">
          총 <span className="font-bold text-white">{total}</span>건
        </div>
      </div>

      {/* 필터 섹션 */}
      <AuditLogsFilter value={filters} onChange={setFilters} />

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
        자동 새로고침: 60초 주기
      </div>
    </div>
  );
}
