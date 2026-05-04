'use client';

import { useAccounts } from '@/components/Providers';
import { useCallback, useEffect, useState } from 'react';
import { Check, X, Clock, Undo2, RefreshCw, Play, Wifi } from 'lucide-react';
import { useEventStream } from '@/lib/hooks/useEventStream';
import { useToast } from '@/lib/hooks/useToast';
import ConfirmationDialog from './ConfirmationDialog';
import ActionHistoryFilter, { FilterState } from './ActionHistoryFilter';

interface Action {
  action_id: string;
  timestamp: string;
  user: string;
  account_id?: string;
  action_type: 'stop_instance' | 'block_bucket' | 'remediate' | 'rollback';
  resource_id: string;
  status: 'success' | 'failed' | 'pending';
  message: string;
}

interface DialogState {
  isOpen: boolean;
  actionId: string | null;
  actionType: Action['action_type'] | null;
  resourceId: string | null;
}

export default function ActionHistory() {
  const { selectedAccountId } = useAccounts();
  const { addToast } = useToast();
  const [actions, setActions] = useState<Action[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [rollingBack, setRollingBack] = useState<string | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DialogState>({ isOpen: false, actionId: null, actionType: null, resourceId: null });
  const [filters, setFilters] = useState<FilterState>({ type: 'all', status: 'all' });

  const loadActions = useCallback(async () => {
    if (!selectedAccountId) return;
    setIsLoading(true);
    try {
      const url = new URL('/api/actions', window.location.origin);
      url.searchParams.set('account_id', selectedAccountId);
      url.searchParams.set('limit', '10');
      if (filters.type !== 'all') url.searchParams.set('type', filters.type);
      if (filters.status !== 'all') url.searchParams.set('status', filters.status);

      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setActions(data.actions || []);
      }
    } catch (error) {
      console.error('Failed to load actions:', error);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAccountId, filters]);

  const handleActionUpdate = useCallback((updatedAction: Action) => {
    setActions(prev => {
      const existing = prev.find(a => a.action_id === updatedAction.action_id);
      if (existing) {
        return prev.map(a => a.action_id === updatedAction.action_id ? updatedAction : a);
      }
      return [updatedAction, ...prev].slice(0, 10);
    });
  }, []);

  const { isConnected } = useEventStream({
    accountId: selectedAccountId || 'default',
    onEvent: handleActionUpdate,
  });

  useEffect(() => {
    loadActions();
  }, [selectedAccountId, filters, loadActions]);

  const handleRollback = async (actionId: string) => {
    setRollingBack(actionId);
    try {
      const res = await fetch('/api/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, account_id: selectedAccountId }),
      });
      if (res.ok) {
        addToast({
          type: 'success',
          title: 'Rollback Successful',
          message: 'The action has been rolled back.',
        });

        // Log to audit log
        await fetch('/api/audit-logs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user: 'admin',
            action: 'rollback',
            resource_id: actionId,
            status: 'success',
            details: { account_id: selectedAccountId },
          }),
        }).catch(err => console.error('Failed to log audit:', err));

        await loadActions();
      } else {
        addToast({
          type: 'error',
          title: 'Rollback Failed',
          message: 'Failed to rollback action. Please try again.',
        });
      }
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Error',
        message: 'Error rolling back action. Please try again.',
      });
    } finally {
      setRollingBack(null);
    }
  };

  const openConfirmDialog = (actionId: string, actionType: Action['action_type'], resourceId: string) => {
    setDialog({
      isOpen: true,
      actionId,
      actionType,
      resourceId,
    });
  };

  const closeConfirmDialog = () => {
    setDialog({ isOpen: false, actionId: null, actionType: null, resourceId: null });
  };

  const handleExecuteAction = async () => {
    if (!dialog.actionId || !dialog.actionType || !selectedAccountId) return;

    setExecuting(dialog.actionId);
    closeConfirmDialog();

    try {
      let endpoint = '';
      let body: Record<string, unknown> = { account_id: selectedAccountId };

      if (dialog.actionType === 'stop_instance') {
        endpoint = '/api/remediate';
        body.action = 'stop_instance';
        body.resource_id = dialog.resourceId;
      } else if (dialog.actionType === 'block_bucket') {
        endpoint = '/api/remediate';
        body.action = 'block_bucket';
        body.resource_id = dialog.resourceId;
      }

      if (!endpoint) return;

      addToast({
        type: 'info',
        title: 'Action Started',
        message: `Executing ${dialog.actionType.replace('_', ' ')}...`,
      });

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        addToast({
          type: 'success',
          title: 'Action Completed',
          message: 'The remediation action has been executed successfully.',
        });

        // Log to audit log
        await fetch('/api/audit-logs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user: 'admin',
            action: dialog.actionType,
            resource_id: dialog.resourceId,
            status: 'success',
            details: { account_id: selectedAccountId },
          }),
        }).catch(err => console.error('Failed to log audit:', err));

        await loadActions();
      } else {
        addToast({
          type: 'error',
          title: 'Action Failed',
          message: 'Failed to execute action. Please try again.',
        });

        // Log failure
        await fetch('/api/audit-logs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user: 'admin',
            action: dialog.actionType,
            resource_id: dialog.resourceId,
            status: 'failed',
            details: { account_id: selectedAccountId, error: 'Action execution failed' },
          }),
        }).catch(err => console.error('Failed to log audit:', err));
      }
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Error',
        message: 'Error executing action. Please try again.',
      });
    } finally {
      setExecuting(null);
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

  const canExecuteAction = (action: Action) => {
    if (action.status === 'pending') return true;
    return false;
  };

  const getDialogConfig = (actionType: Action['action_type']) => {
    const configs = {
      stop_instance: {
        title: 'Stop EC2 Instance?',
        message: 'This will immediately stop the EC2 instance. You can restart it later from the AWS console.',
        confirmText: 'Stop Instance',
      },
      block_bucket: {
        title: 'Block S3 Bucket Public Access?',
        message: 'This will enable all public access block settings on the S3 bucket.',
        confirmText: 'Block Access',
      },
      remediate: {
        title: 'Execute Remediation?',
        message: 'This will execute the remediation action on the resource.',
        confirmText: 'Remediate',
      },
      rollback: {
        title: 'Rollback Action?',
        message: 'This will undo the previous action.',
        confirmText: 'Rollback',
      },
    };
    return configs[actionType];
  };

  const dialogConfig = dialog.actionType ? getDialogConfig(dialog.actionType) : null;

  return (
    <>
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-semibold text-slate-100">Action History</h2>
            {isConnected && (
              <div title="Live stream active">
                <Wifi className="w-4 h-4 text-green-400" />
              </div>
            )}
          </div>
          <button
            onClick={loadActions}
            disabled={isLoading}
            className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <ActionHistoryFilter onFilterChange={setFilters} />

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

                <div className="ml-3 flex items-center gap-2">
                  {action.status === 'pending' && (action.action_type === 'stop_instance' || action.action_type === 'block_bucket') && (
                    <button
                      onClick={() => openConfirmDialog(action.action_id, action.action_type, action.resource_id)}
                      disabled={executing === action.action_id}
                      className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-amber-400 hover:border-amber-400/50 transition-colors disabled:opacity-50"
                      title="Execute this action"
                    >
                      <Play className={`w-4 h-4 ${executing === action.action_id ? 'animate-spin' : ''}`} />
                    </button>
                  )}

                  {action.status === 'success' && isRecentEnough(action.timestamp) && (
                    <button
                      onClick={() => handleRollback(action.action_id)}
                      disabled={rollingBack === action.action_id}
                      className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-blue-400 hover:border-blue-400/50 transition-colors disabled:opacity-50"
                      title="Undo this action"
                    >
                      <Undo2 className={`w-4 h-4 ${rollingBack === action.action_id ? 'animate-spin' : ''}`} />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {dialogConfig && (
        <ConfirmationDialog
          isOpen={dialog.isOpen}
          title={dialogConfig.title}
          message={`${dialogConfig.message}\n\nResource: ${dialog.resourceId}`}
          confirmText={dialogConfig.confirmText}
          isDangerous={true}
          isLoading={executing === dialog.actionId}
          onConfirm={handleExecuteAction}
          onCancel={closeConfirmDialog}
        />
      )}
    </>
  );
}
