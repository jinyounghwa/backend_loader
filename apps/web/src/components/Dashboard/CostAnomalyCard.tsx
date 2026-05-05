'use client';

import { TrendingUp, AlertTriangle } from 'lucide-react';
import type { CostAnomaly } from '@/lib/hooks/useCostAnomalies';

interface CostAnomalyCardProps {
  anomalies: CostAnomaly[];
  loading?: boolean;
}

export default function CostAnomalyCard({ anomalies, loading }: CostAnomalyCardProps) {
  if (loading) {
    return (
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-4 h-64 flex items-center justify-center">
        <div className="animate-pulse text-slate-500">Analyzing costs...</div>
      </div>
    );
  }

  if (anomalies.length === 0) {
    return (
      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-4">
        <div className="flex items-center mb-3">
          <TrendingUp className="w-5 h-5 mr-2 text-slate-400" />
          <h3 className="font-semibold text-slate-200 text-sm">Cost Stability</h3>
        </div>
        <div className="text-slate-500 text-xs text-center py-8">✅ No cost anomalies detected</div>
      </div>
    );
  }

  return (
    <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4">
      <div className="flex items-center mb-3">
        <AlertTriangle className="w-5 h-5 mr-2 text-amber-500" />
        <h3 className="font-semibold text-amber-400 text-sm">{anomalies.length} Cost Spike(s)</h3>
      </div>
      <div className="space-y-2">
        {anomalies.map((anomaly) => (
          <div
            key={anomaly.region}
            className="bg-slate-800/50 rounded p-2.5 text-xs text-slate-300"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-slate-400">{anomaly.region}</span>
              <span className="text-amber-400 font-semibold">
                +{anomaly.spike_percent.toFixed(1)}%
              </span>
            </div>
            <div className="text-slate-500 text-xs mb-1">
              ${anomaly.today_cost.toFixed(2)} vs avg ${anomaly.avg_7day.toFixed(2)}
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-1">
              <div
                className="bg-amber-500 h-1 rounded-full"
                style={{
                  width: `${Math.min(
                    (anomaly.spike_percent / 50) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
