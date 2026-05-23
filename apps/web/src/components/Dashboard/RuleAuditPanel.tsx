'use client';

import { useState, useEffect } from 'react';
import { Filter, AlertCircle, CheckCircle, Trash2, Upload, RotateCcw, Edit } from 'lucide-react';
import { SecurityRule } from '@/lib/hooks/useSecurityRules';

interface AuditLog {
  rule_id: string;
  audit_id: string;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'DEPLOY' | 'ROLLBACK';
  timestamp: string;
  user_id?: string;
  status: 'SUCCESS' | 'FAILURE';
  error_message?: string;
  details?: Record<string, any>;
}

interface RuleAuditPanelProps {
  rule?: SecurityRule;
}

export function RuleAuditPanel({ rule }: RuleAuditPanelProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [summary, setSummary] = useState<any>(null);

  // Load audit logs
  useEffect(() => {
    if (rule?.rule_id) {
      loadAuditLogs();
    }
  }, [rule?.rule_id, selectedAction]);

  const loadAuditLogs = async () => {
    if (!rule?.rule_id) return;

    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        rule_id: rule.rule_id,
        limit: '50',
      });

      if (selectedAction) {
        params.append('action', selectedAction);
      }

      const response = await fetch(
        `/api/guardian/rules/audit?${params.toString()}`
      );

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
        setSummary(data.summary);
      } else {
        console.warn('Failed to load audit logs');
        setLogs([]);
      }
    } catch (err) {
      console.error('Error loading audit logs:', err);
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'CREATE':
        return <Edit className="w-4 h-4" />;
      case 'UPDATE':
        return <Edit className="w-4 h-4" />;
      case 'DELETE':
        return <Trash2 className="w-4 h-4" />;
      case 'DEPLOY':
        return <Upload className="w-4 h-4" />;
      case 'ROLLBACK':
        return <RotateCcw className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getActionColor = (action: string): string => {
    switch (action) {
      case 'CREATE':
        return 'bg-blue-500/10 text-blue-400';
      case 'UPDATE':
        return 'bg-yellow-500/10 text-yellow-400';
      case 'DELETE':
        return 'bg-red-500/10 text-red-400';
      case 'DEPLOY':
        return 'bg-green-500/10 text-green-400';
      case 'ROLLBACK':
        return 'bg-orange-500/10 text-orange-400';
      default:
        return 'bg-gray-500/10 text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    return status === 'SUCCESS' ? (
      <CheckCircle className="w-4 h-4 text-green-400" />
    ) : (
      <AlertCircle className="w-4 h-4 text-red-400" />
    );
  };

  const formatDate = (isoString: string): string => {
    try {
      return new Date(isoString).toLocaleString('ko-KR');
    } catch {
      return isoString;
    }
  };

  const allActions = summary?.action_counts ? Object.keys(summary.action_counts) : [];

  return (
    <div className="space-y-4">
      {/* Audit Summary */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <div className="p-3 bg-slate-800 rounded-lg border border-slate-700">
            <div className="text-xs text-gray-400 mb-1">전체 로그</div>
            <div className="text-xl font-bold text-white">{summary.total_logs}</div>
          </div>
          {allActions.map((action) => (
            <div key={action} className="p-3 bg-slate-800 rounded-lg border border-slate-700">
              <div className="text-xs text-gray-400 mb-1">{action}</div>
              <div className="text-xl font-bold text-white">{summary.action_counts[action]}</div>
            </div>
          ))}
        </div>
      )}

      {/* Action Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setSelectedAction(null)}
          className={`flex items-center gap-2 px-3 py-1 rounded text-sm font-medium transition-colors ${
            selectedAction === null
              ? 'bg-blue-600 text-white'
              : 'bg-slate-800 text-gray-300 hover:bg-slate-700'
          }`}
        >
          <Filter className="w-3 h-3" />
          모두
        </button>
        {allActions.map((action) => (
          <button
            key={action}
            onClick={() => setSelectedAction(action)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              selectedAction === action
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-gray-300 hover:bg-slate-700'
            }`}
          >
            {action}
          </button>
        ))}
      </div>

      {/* Audit Log Timeline */}
      <div className="space-y-2">
        <h3 className="text-lg font-bold text-white">감사 로그</h3>

        {isLoading ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            로드 중...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            감사 로그가 없습니다
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div
                key={log.audit_id}
                className="p-3 bg-slate-800 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors"
              >
                {/* Log Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {/* Action Badge */}
                    <span
                      className={`inline-flex items-center gap-2 px-2 py-1 rounded text-xs font-semibold ${getActionColor(
                        log.action
                      )}`}
                    >
                      {getActionIcon(log.action)}
                      {log.action}
                    </span>

                    {/* Status */}
                    <div className="flex items-center gap-1">
                      {getStatusIcon(log.status)}
                      <span className="text-xs text-gray-400">{log.status}</span>
                    </div>
                  </div>

                  {/* Timestamp */}
                  <div className="text-xs text-gray-500">{formatDate(log.timestamp)}</div>
                </div>

                {/* User Info */}
                {log.user_id && (
                  <div className="text-xs text-gray-400 mb-1">
                    사용자: <span className="text-gray-300">{log.user_id}</span>
                  </div>
                )}

                {/* Error Message */}
                {log.error_message && (
                  <div className="text-xs text-red-400 mt-1">
                    오류: {log.error_message}
                  </div>
                )}

                {/* Details */}
                {log.details && Object.keys(log.details).length > 0 && (
                  <div className="text-xs text-gray-500 mt-2">
                    <details className="cursor-pointer">
                      <summary className="text-gray-400">상세 정보</summary>
                      <pre className="mt-1 p-2 bg-slate-900 rounded text-xs overflow-auto max-h-40">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 text-xs text-gray-400">
        <div>
          모든 규칙 변경 사항이 자동으로 기록됩니다. CREATE, UPDATE, DELETE, DEPLOY, ROLLBACK 작업을 추적할 수 있습니다.
        </div>
      </div>
    </div>
  );
}
