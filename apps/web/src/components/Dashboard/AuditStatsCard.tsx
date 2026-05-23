'use client';

import { useAuditStatistics } from '@/lib/hooks/useAuditStatistics';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Download } from 'lucide-react';
import { exportAuditLogs } from '@/lib/utils/export';

interface AuditStatsCardProps {
  accountId?: string;
  connectionId?: string;
  startTime?: string;
  endTime?: string;
}

const COLORS = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899'];

export function AuditStatsCard({
  accountId,
  connectionId,
  startTime,
  endTime,
}: AuditStatsCardProps) {
  const { statistics, isLoading, error } = useAuditStatistics({
    accountId,
    connectionId,
    startTime,
    endTime,
  });

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      await exportAuditLogs({
        accountId,
        connectionId,
        startTime,
        endTime,
        format,
      });
    } catch (err) {
      console.error('Export failed:', err);
      alert(`Export failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-gray-400">통계 로드 중...</div>
      </div>
    );
  }

  if (error || !statistics) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-red-400">통계 로드 실패</div>
      </div>
    );
  }

  const eventTypeData = Object.entries(statistics.event_types || {}).map(([name, count]) => ({
    name,
    count,
  }));

  const statusData = Object.entries(statistics.status_distribution || {}).map(([name, count]) => ({
    name,
    value: count,
  }));

  return (
    <div className="space-y-6">
      {/* 요약 통계 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-gray-400 text-sm">총 이벤트</div>
          <div className="text-2xl font-bold text-white mt-1">{statistics.total_events}</div>
        </div>

        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-gray-400 text-sm">성공률</div>
          <div className="text-2xl font-bold text-green-500 mt-1">
            {statistics.success_rate.toFixed(1)}%
          </div>
        </div>

        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-gray-400 text-sm">계정 수</div>
          <div className="text-2xl font-bold text-blue-500 mt-1">
            {statistics.top_accounts?.length || 0}
          </div>
        </div>

        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-gray-400 text-sm">연결 수</div>
          <div className="text-2xl font-bold text-purple-500 mt-1">
            {statistics.top_connections?.length || 0}
          </div>
        </div>
      </div>

      {/* 이벤트 타입 차트 */}
      {eventTypeData.length > 0 && (
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <h3 className="text-lg font-bold text-white mb-4">이벤트 타입별 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={eventTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="name" stroke="#cbd5e1" />
              <YAxis stroke="#cbd5e1" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Bar dataKey="count" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 상태 분포 파이 차트 */}
      {statusData.length > 0 && (
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <h3 className="text-lg font-bold text-white mb-4">상태 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Export 버튼 */}
      <div className="flex gap-2">
        <button
          onClick={() => handleExport('json')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
        >
          <Download className="w-4 h-4" />
          JSON 다운로드
        </button>

        <button
          onClick={() => handleExport('csv')}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
        >
          <Download className="w-4 h-4" />
          CSV 다운로드
        </button>
      </div>
    </div>
  );
}
