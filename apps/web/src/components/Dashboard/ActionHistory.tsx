'use client';

import { useAccounts } from '@/components/Providers';
import { useEffect, useState } from 'react';
import { Check, X, Clock, Undo2, RefreshCw } from 'lucide-react';

interface Action {
  action_id: string;
  timestamp: string;
  user: string;
  action_type: 'stop_instance' | 'block_bucket' | 'remediate' | 'rollback';
  resource_id: string;
  status: 'success' | 'failed' | 'pending';
  message: string;
}

export default function ActionHistory() {
  const { selectedAccountId } = useAccounts();
  const [actions, setActions] = useState<Action[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [rollingBack, setRollingBack] = useState<string | null>(null);

  const loadActions = async () => {
    if (!selectedAccountId) return;
    setIsLoading(true);
    try {
      const res = await fetch(`/api/actions?account_id=${selectedAccountId}&limit=10`);
      if (res.ok) {
        const data = await res.json();
        setActions(data.actions || []);
      }
    } catch (error) {
      console.error('Failed to load actions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadActions();
  }, [selectedAccountId]);

  const handleRollback = async (actionId: string) => {
    setRollingBack(actionId);
    try {
      const res = await fetch('/api/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, account_id: selectedAccountId }),
      });
      if (res.ok) {
        await loadActions();
      }
    } finally {
      setRollingBack(null);
    }
  };

  const getActionLabel = (type: Action['action_type']) => {
    const labels = {
      stop_instance: 'Stop Instance',
      block_bucket: 'Block Bucket',
      remediate: 'Remediate',
      rollback: 'Rollback',
    };
    return labels[type] || type;
  };

  const getStatusIcon = (status: Action['status']) => {
    switch (status) {
      case 'success':
        return <Check className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <X className="w-4 h-4 text-red-400" />;
      default:
        return <Clock className="w-4 h-4 text-blue-400" />;
    }
  };

  const isRecentEnough = (timestamp: string) => {
    const age = Date.now() - new Date(timestamp).getTime();
    return age < 3600000;
  };

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-100">Action History</h2>
        <button
          onClick={loadActions}
          disabled={isLoading}
          className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {actions.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p className="text-sm">No recent actions</p>
          </div>
        ) : (
          actions.map(action => (
            <div key={action.action_id} className="flex items-start justify-between p-3 rounded-lg border border-slate-700/50 hover:border-slate-600 transition-colors">
              <div className="flex items-start space-x-3 flex-1">
                <div className="mt-1">{getStatusIcon(action.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <p className="text-sm font-medium text-slate-100">{getActionLabel(action.action_type)}</p>
                    <span className="text-xs text-slate-500">on {action.resource_id}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{action.message}</p>
                  <div className="flex items-center space-x-2 mt-2 text-xs text-slate-500">
                    <span>{action.user}</span>
                    <span>•</span>
                    <span>{new Date(action.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              </div>

              {action.status === 'success' && isRecentEnough(action.timestamp) && (
                <button
                  onClick={() => handleRollback(action.action_id)}
                  disabled={rollingBack === action.action_id}
                  className="ml-3 p-1.5 rounded border border-slate-700 text-slate-400 hover:text-blue-400 hover:border-blue-400/50 transition-colors disabled:opacity-50"
                  title="Undo this action"
                >
                  <Undo2 className={`w-4 h-4 ${rollingBack === action.action_id ? 'animate-spin' : ''}`} />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
