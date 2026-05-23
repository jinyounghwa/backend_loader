'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, XCircle, Clock } from 'lucide-react';

interface Alert {
  alert_id: string;
  rule_id: string;
  severity: number;
  account_id: string;
  timestamp: string;
  message: string;
  status: 'sent' | 'failed' | 'retried';
  created_at: string;
}

export function AlertHistory() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setIsLoading(true);
        // In a real implementation, this would fetch from an API
        // For now, we'll show an empty state
        setAlerts([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const getSeverityColor = (severity: number): string => {
    if (severity >= 9) return 'border-l-red-500 bg-red-500/10';
    if (severity >= 7) return 'border-l-orange-500 bg-orange-500/10';
    if (severity >= 5) return 'border-l-yellow-500 bg-yellow-500/10';
    return 'border-l-blue-500 bg-blue-500/10';
  };

  const getSeverityEmoji = (severity: number): string => {
    if (severity >= 9) return '🚨';
    if (severity >= 7) return '⚠️';
    if (severity >= 5) return '⚡';
    return 'ℹ️';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'retried':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-gray-400">로드 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-red-400">알림 이력 로드 실패: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">알림 이력</h3>
        <span className="text-sm text-gray-400">{alerts.length}개</span>
      </div>

      {alerts.length === 0 ? (
        <div className="p-8 bg-slate-800 rounded-lg border border-slate-700 text-center">
          <div className="text-gray-400">최근 알림이 없습니다</div>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {alerts.map((alert) => (
            <div
              key={alert.alert_id}
              className={`p-4 rounded-lg border-l-4 ${getSeverityColor(alert.severity)}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">{getSeverityEmoji(alert.severity)}</span>
                    <span className="font-bold text-white">[{alert.account_id}]</span>
                    <span className="text-white">{alert.message}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <span>규칙: {alert.rule_id}</span>
                    <span>심각도: {alert.severity}/10</span>
                    <span>
                      {new Date(alert.timestamp).toLocaleString('ko-KR')}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(alert.status)}
                  <span className="text-xs text-gray-400 capitalize">
                    {alert.status === 'sent'
                      ? '발송됨'
                      : alert.status === 'failed'
                        ? '실패'
                        : '재시도'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
