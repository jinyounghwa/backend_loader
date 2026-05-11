'use client';

import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import GuardianStatusCard from '@/components/Dashboard/GuardianStatusCard';
import GuardianEventLog from '@/components/Dashboard/GuardianEventLog';
import GuardianActionHistory from '@/components/Dashboard/GuardianActionHistory';
import GuardianThreatAnalysis from '@/components/Dashboard/GuardianThreatAnalysis';

interface DashboardStatus {
  version: string;
  timestamp: string;
  ec2: {
    total_instances: number;
    running: number;
    stopped: number;
    unauthorized_regions: number;
    security_issues: number;
    status: 'healthy' | 'alert' | 'warning';
  };
  s3: {
    total_buckets: number;
    secure_buckets: number;
    public_buckets: number;
    encryption_enabled: number;
    versioning_enabled: number;
    status: 'healthy' | 'alert' | 'warning';
  };
  cost: {
    daily_cost: number;
    daily_threshold: number;
    monthly_estimate: number;
    within_budget: boolean;
    trend: 'up' | 'down';
    status: 'healthy' | 'alert' | 'warning';
  };
  cache: {
    backend: string;
    hit_rate: number;
    connected: boolean;
    status: 'healthy' | 'alert' | 'warning';
  };
  lambda: {
    last_execution: string;
    execution_time_ms: number;
    error_count: number;
    status: 'healthy' | 'alert' | 'warning';
  };
  overall_health: 'healthy' | 'alert' | 'warning';
}

export default function DashboardPage() {
  const [status, setStatus] = useState<DashboardStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/guardian/status');
      if (!response.ok) throw new Error('Failed to fetch status');

      const data = await response.json();
      setStatus(data);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-100">AWS Guardian Dashboard</h1>
            <p className="mt-2 text-slate-400">Real-time monitoring and threat detection</p>
          </div>
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {lastRefresh && (
          <div className="text-sm text-slate-400">
            Last updated: {lastRefresh.toLocaleTimeString()} | Version: {status?.version || 'N/A'}
          </div>
        )}

        {/* Health Status Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {status && (
            <>
              <GuardianStatusCard
                title="EC2"
                status={status.ec2.status}
                stats={{
                  total: status.ec2.total_instances,
                  running: status.ec2.running,
                  stopped: status.ec2.stopped,
                  issues: status.ec2.security_issues,
                }}
              />
              <GuardianStatusCard
                title="S3"
                status={status.s3.status}
                stats={{
                  total: status.s3.total_buckets,
                  secure: status.s3.secure_buckets,
                  public: status.s3.public_buckets,
                  issues: status.s3.total_buckets - status.s3.secure_buckets,
                }}
              />
              <GuardianStatusCard
                title="Cost"
                status={status.cost.status}
                stats={{
                  daily: Math.round(status.cost.daily_cost * 100) / 100,
                  threshold: status.cost.daily_threshold,
                  monthly: Math.round(status.cost.monthly_estimate * 100) / 100,
                  issues: status.cost.within_budget ? 0 : 1,
                }}
              />
            </>
          )}
        </div>

        {/* System Status */}
        {status && (
          <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">System Status</h2>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Cache Backend</div>
                <div className="mt-1 text-lg font-semibold text-slate-100">{status.cache.backend}</div>
                <div className="mt-2 text-xs text-slate-400">Hit Rate: {(status.cache.hit_rate * 100).toFixed(1)}%</div>
              </div>
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Lambda</div>
                <div className="mt-1 text-lg font-semibold text-slate-100">
                  {status.lambda.execution_time_ms}ms
                </div>
                <div className="mt-2 text-xs text-slate-400">Errors: {status.lambda.error_count}</div>
              </div>
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">Overall Health</div>
                <div className={`mt-1 text-lg font-semibold capitalize ${
                  status.overall_health === 'healthy'
                    ? 'text-green-400'
                    : status.overall_health === 'warning'
                      ? 'text-yellow-400'
                      : 'text-red-400'
                }`}>
                  {status.overall_health}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Threat Analysis */}
        <GuardianThreatAnalysis />

        {/* Event Log and Action History */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <GuardianEventLog limit={10} />
          <GuardianActionHistory limit={10} />
        </div>
      </div>
    </div>
  );
}
