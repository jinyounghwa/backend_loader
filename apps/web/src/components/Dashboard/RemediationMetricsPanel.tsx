'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, TrendingUp } from 'lucide-react';

interface RuleMetric {
  rule_id: string;
  action_type: string;
  total_actions: number;
  successful_actions: number;
  success_rate: number;
  resolved_issues: number;
  resolution_rate: number;
  effectiveness_score: number;
}

interface MetricsResponse {
  metrics: RuleMetric[];
  summary: {
    total_rules: number;
    avg_effectiveness_score: number;
    avg_success_rate: number;
    avg_resolution_rate: number;
  };
}

export default function RemediationMetricsPanel() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/remediation-metrics');
        if (!response.ok) throw new Error('Failed to fetch');
        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5 h-96 flex items-center justify-center">
        <div className="animate-pulse text-slate-500">Loading metrics...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
        <div className="text-red-400 text-sm">{error || 'Failed to load metrics'}</div>
      </div>
    );
  }

  const { metrics, summary } = data;

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
      <div className="p-5 border-b border-slate-800">
        <h2 className="text-lg font-bold text-slate-200 flex items-center">
          <TrendingUp className="w-5 h-5 mr-2 text-slate-400" />
          Remediation Effectiveness
        </h2>
      </div>

      <div className="p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <MetricCard
            label="Avg Effectiveness"
            value={`${(summary.avg_effectiveness_score * 100).toFixed(0)}%`}
            color="text-green-500"
          />
          <MetricCard
            label="Success Rate"
            value={`${(summary.avg_success_rate * 100).toFixed(0)}%`}
            color="text-blue-500"
          />
          <MetricCard
            label="Resolution Rate"
            value={`${(summary.avg_resolution_rate * 100).toFixed(0)}%`}
            color="text-amber-500"
          />
          <MetricCard
            label="Active Rules"
            value={summary.total_rules.toString()}
            color="text-slate-400"
          />
        </div>

        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500 px-2">Per-Rule Breakdown</h3>
          {metrics.map((rule) => (
            <RuleMetricRow key={rule.rule_id} rule={rule} />
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-slate-800/40 rounded p-3">
      <div className="text-xs text-slate-500 uppercase font-mono mb-1">{label}</div>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

function RuleMetricRow({ rule }: { rule: RuleMetric }) {
  const effectivenessColor =
    rule.effectiveness_score >= 0.9
      ? 'bg-green-500/20 text-green-400'
      : rule.effectiveness_score >= 0.8
        ? 'bg-blue-500/20 text-blue-400'
        : 'bg-amber-500/20 text-amber-400';

  return (
    <div className="bg-slate-800/30 rounded p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-mono text-slate-300">{rule.rule_id}</div>
          <div className="text-xs text-slate-500">{rule.action_type}</div>
        </div>
        <div className={`px-2 py-1 rounded text-sm font-semibold ${effectivenessColor}`}>
          {(rule.effectiveness_score * 100).toFixed(0)}%
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-slate-500 mb-0.5">Success</div>
          <div className="text-slate-300 font-mono">
            {rule.successful_actions}/{rule.total_actions}
          </div>
        </div>
        <div>
          <div className="text-slate-500 mb-0.5">Resolved</div>
          <div className="text-slate-300 font-mono">
            {rule.resolved_issues}/{rule.total_actions}
          </div>
        </div>
        <div>
          <div className="text-slate-500 mb-0.5">Rate</div>
          <div className="text-slate-300 font-mono">
            {(rule.resolution_rate * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      <div className="w-full bg-slate-700/50 rounded-full h-1">
        <div
          className="bg-green-500 h-1 rounded-full"
          style={{ width: `${rule.effectiveness_score * 100}%` }}
        />
      </div>
    </div>
  );
}
