'use client';

import { AuditLog } from '@/app/api/guardian/audit-logs/route';
import { AlertCircle, CheckCircle, MessageCircle, Radio } from 'lucide-react';

interface AuditLogsTimelineProps {
  logs: AuditLog[];
  isLoading: boolean;
}

export function AuditLogsTimeline({ logs, isLoading }: AuditLogsTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-3 p-4 bg-slate-800 rounded-lg border border-slate-700">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-20 bg-slate-700/50 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="p-8 bg-slate-800 rounded-lg border border-slate-700 text-center">
        <AlertCircle className="w-12 h-12 text-gray-500 mx-auto mb-3" />
        <p className="text-gray-400">조회된 로그가 없습니다</p>
      </div>
    );
  }

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case '$connect':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case '$disconnect':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'message':
        return <MessageCircle className="w-5 h-5 text-blue-500" />;
      case 'broadcast':
        return <Radio className="w-5 h-5 text-amber-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getEventTypeLabel = (eventType: string) => {
    switch (eventType) {
      case '$connect':
        return '연결';
      case '$disconnect':
        return '연결 해제';
      case 'message':
        return '메시지';
      case 'broadcast':
        return '브로드캐스트';
      default:
        return eventType;
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'success'
      ? 'text-green-400'
      : status === 'error'
        ? 'text-red-400'
        : 'text-gray-400';
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('ko-KR', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="space-y-3 p-4 bg-slate-800 rounded-lg border border-slate-700">
      {logs.map((log) => (
        <div
          key={`${log.timestamp}-${log.event_type}`}
          className="flex gap-4 p-4 bg-slate-700/50 rounded-lg border border-slate-600 hover:border-slate-500 transition-colors"
        >
          <div className="flex-shrink-0 flex items-start pt-1">
            {getEventIcon(log.event_type)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white">
                  {getEventTypeLabel(log.event_type)}
                </span>
                <span className={`text-xs font-medium ${getStatusColor(log.status)}`}>
                  {log.status}
                </span>
              </div>
              <span className="text-xs text-gray-400 flex-shrink-0">
                {formatTimestamp(log.timestamp)}
              </span>
            </div>

            <div className="space-y-1 text-sm">
              {log.user_id && (
                <p className="text-gray-300">
                  <span className="text-gray-500">사용자:</span> {log.user_id}
                </p>
              )}

              {log.message_type && (
                <p className="text-gray-300">
                  <span className="text-gray-500">타입:</span> {log.message_type}
                </p>
              )}

              {log.threat_score !== undefined && (
                <p className="text-gray-300">
                  <span className="text-gray-500">위협:</span> {log.threat_score}/10
                </p>
              )}

              {log.details && Object.keys(log.details).length > 0 && (
                <p className="text-gray-400 text-xs mt-2">
                  <span className="text-gray-500">세부사항:</span>{' '}
                  {JSON.stringify(log.details, null, 2)}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
