'use client';

import { useInsights, AnomalyInput, InsightsData } from '@/lib/hooks/useInsights';
import { AlertCircle, TrendingUp, Shield, RefreshCw } from 'lucide-react';
import { useCallback } from 'react';

interface InsightsPanelProps {
  anomalies: AnomalyInput[];
  onRefresh?: () => void;
}

export default function InsightsPanel({ anomalies, onRefresh }: InsightsPanelProps) {
  const { insights, loading, error, analyze } = useInsights();

  const handleAnalyze = useCallback(async () => {
    if (anomalies.length === 0) return;
    await analyze(anomalies);
    onRefresh?.();
  }, [anomalies, analyze, onRefresh]);

  if (anomalies.length === 0) {
    return (
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
        <div className="text-slate-500 text-sm text-center py-8">
          No anomalies detected — no insights to correlate
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-slate-200 flex items-center">
          <Shield className="w-5 h-5 mr-2 text-slate-400" />
          Cross-Region Insights
        </h2>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="flex items-center px-3 py-2 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          <span className="text-xs font-medium">Analyze</span>
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {insights ? (
        <InsightView insights={insights} />
      ) : (
        <div className="text-slate-500 text-sm text-center py-12">
          {loading ? 'Analyzing anomalies...' : 'Click "Analyze" to correlate anomalies'}
        </div>
      )}
    </div>
  );
}

function InsightView({ insights }: { insights: InsightsData }) {
  const urgencyColor =
    insights.urgency >= 8
      ? 'text-red-500'
      : insights.urgency >= 5
        ? 'text-amber-500'
        : 'text-blue-500';

  const confidenceIcon =
    insights.confidence === 'high' ? '🔴' : insights.confidence === 'medium' ? '🟡' : '🔵';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-slate-800/40 rounded p-3">
          <div className="text-xs text-slate-500 uppercase font-mono mb-1">Correlation Score</div>
          <div className="text-2xl font-bold text-slate-100">
            {(insights.correlation_score * 100).toFixed(0)}%
          </div>
          <div className="mt-2 w-full bg-slate-700 rounded-full h-1">
            <div
              className="bg-blue-500 h-1 rounded-full transition-all"
              style={{ width: `${insights.correlation_score * 100}%` }}
            />
          </div>
        </div>

        <div className="bg-slate-800/40 rounded p-3">
          <div className="text-xs text-slate-500 uppercase font-mono mb-1">Urgency Level</div>
          <div className={`text-2xl font-bold ${urgencyColor}`}>{insights.urgency}/10</div>
          <div className="text-xs text-slate-400 mt-2">
            {insights.urgency >= 8
              ? 'CRITICAL'
              : insights.urgency >= 5
                ? 'HIGH'
                : 'MODERATE'}
          </div>
        </div>
      </div>

      <div className="bg-slate-800/40 rounded p-3">
        <div className="flex items-start justify-between mb-2">
          <div className="text-xs text-slate-500 uppercase font-mono">Threat Type</div>
          <span className="text-xs px-2 py-1 rounded bg-slate-700/50 text-slate-300">
            {confidenceIcon} {insights.confidence.toUpperCase()}
          </span>
        </div>
        <div className="text-sm font-semibold text-slate-100">{insights.threat_type}</div>
      </div>

      <div className="bg-slate-800/40 rounded p-3">
        <div className="text-xs text-slate-500 uppercase font-mono mb-1.5">Recommendation</div>
        <p className="text-sm text-slate-300 leading-relaxed">{insights.recommendation}</p>
      </div>

      {insights.cost_impact !== undefined && insights.cost_impact > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded p-3">
          <div className="flex items-center mb-1">
            <TrendingUp className="w-4 h-4 mr-1.5 text-amber-500" />
            <span className="text-xs font-semibold text-amber-400">COST IMPACT</span>
          </div>
          <div className="text-sm text-amber-300">${insights.cost_impact}/day estimated</div>
        </div>
      )}

      {insights.remediation_rate !== undefined && (
        <div className="text-xs text-slate-500 text-center py-2">
          Remediation effectiveness: {(insights.remediation_rate * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}
