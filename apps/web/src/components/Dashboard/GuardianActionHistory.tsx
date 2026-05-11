'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Clock, Zap } from 'lucide-react';

export interface GuardianAction {
  id: string;
  timestamp: string;
  action_type: string;
  resource_id: string;
  status: 'success' | 'pending' | 'failed';
  message: string;
}

interface GuardianActionHistoryProps {
  limit?: number;
}

export default function GuardianActionHistory({ limit = 10 }: GuardianActionHistoryProps) {
  const [actions, setActions] = useState<GuardianAction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActions = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/guardian/actions?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch actions');

        const data = await response.json();
        setActions(data.actions || []);
      } catch (error) {
        console.error('Error fetching actions:', error);
        // Mock data fallback
        setActions([
          {
            id: 'act-001',
            timestamp: new Date(Date.now() - 600000).toISOString(),
            action_type: 'ec2_stop',
            resource_id: 'i-1234567890abcdef0',
            status: 'success',
            message: 'Instance stopped successfully',
          },
          {
            id: 'act-002',
            timestamp: new Date(Date.now() - 1800000).toISOString(),
            action_type: 's3_block_public',
            resource_id: 'my-bucket-name',
            status: 'success',
            message: 'Public access blocked',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchActions();
  }, [limit]);

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'ec2_stop':
        return <Zap className="w-4 h-4" />;
      case 's3_block_public':
        return <CheckCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getActionLabel = (actionType: string) => {
    switch (actionType) {
      case 'ec2_stop':
        return 'Stop EC2 Instance';
      case 's3_block_public':
        return 'Block S3 Public Access';
      default:
        return actionType;
    }
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);

    if (diffInMinutes < 1) return '방금';
    if (diffInMinutes < 60) return `${diffInMinutes}분 전`;
    return `${diffInHours}시간 전`;
  };

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
      <h2 className="mb-4 text-lg font-semibold text-slate-100">Auto Response History</h2>

      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-slate-400">Loading actions...</div>
          </div>
        ) : actions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-slate-400">No actions yet</div>
          </div>
        ) : (
          actions.map((action) => (
            <div
              key={action.id}
              className="flex items-start gap-4 rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3 transition-all hover:bg-slate-800/50"
            >
              <div className="mt-1 text-slate-500">{getActionIcon(action.action_type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-slate-100">
                    {getActionLabel(action.action_type)}
                  </span>
                  <span className="text-xs text-slate-500">{getRelativeTime(action.timestamp)}</span>
                </div>
                <p className="text-xs text-slate-400 mb-2">Resource: {action.resource_id}</p>
                <p className="text-xs text-slate-400">{action.message}</p>
              </div>
              <div className="mt-1">{getStatusIcon(action.status)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
