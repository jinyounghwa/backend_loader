'use client';

import { useEffect, useState } from 'react';
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

interface AuditLog {
  log_id: string;
  timestamp: string;
  user: string;
  action: string;
  resource_id: string;
  status: 'success' | 'failed';
  details?: Record<string, unknown>;
}

interface AuditLogViewerProps {
  limit?: number;
}

export default function AuditLogViewer({ limit = 50 }: AuditLogViewerProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/audit-logs?limit=${limit}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [limit]);

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      stop_instance: 'Stop Instance',
      block_bucket: 'Block Bucket',
      remediate: 'Remediate',
      rollback: 'Rollback',
    };
    return labels[action] || action;
  };

  const formatDetails = (details?: Record<string, unknown>) => {
    if (!details || Object.keys(details).length === 0) return '-';
    return Object.entries(details)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')
      .substring(0, 50) + '...';
  };

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-100">Audit Logs</h2>
        <button
          onClick={loadLogs}
          disabled={isLoading}
          className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                Timestamp
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                User
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                Action
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                Resource
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                Status
              </th>
              <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400">
                Details
              </th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">
                  No audit logs
                </td>
              </tr>
            ) : (
              logs.map(log => (
                <tr key={log.log_id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                  <td className="px-3 py-2 text-slate-300">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-slate-300">{log.user}</td>
                  <td className="px-3 py-2 text-slate-300">{getActionLabel(log.action)}</td>
                  <td className="px-3 py-2 text-slate-300 font-mono text-xs">{log.resource_id}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center space-x-1">
                      {log.status === 'success' ? (
                        <>
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          <span className="text-green-400">Success</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-4 h-4 text-red-400" />
                          <span className="text-red-400">Failed</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-slate-400 text-xs">{formatDetails(log.details)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-xs text-slate-500">
        Total: {logs.length} log(s) • Showing {Math.min(logs.length, limit)} most recent
      </div>
    </div>
  );
}
