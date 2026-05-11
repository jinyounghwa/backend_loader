'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, Zap } from 'lucide-react';

export interface ThreatAnalysis {
  threat_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  findings: {
    public_buckets: number;
    unauthorized_regions: number;
    high_cost_spike: boolean;
    anomalous_api_activity: boolean;
  };
  recommendations: string[];
  timestamp: string;
}

export default function GuardianThreatAnalysis() {
  const [threat, setThreat] = useState<ThreatAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchThreats = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/guardian/threats');
        if (!response.ok) throw new Error('Failed to fetch threats');

        const data = await response.json();
        setThreat(data);
      } catch (error) {
        console.error('Error fetching threats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchThreats();
    const interval = setInterval(fetchThreats, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'text-green-400';
      case 'medium':
        return 'text-yellow-400';
      case 'high':
        return 'text-orange-400';
      case 'critical':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  const getRiskBgColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-500/10 border-green-500/20';
      case 'medium':
        return 'bg-yellow-500/10 border-yellow-500/20';
      case 'high':
        return 'bg-orange-500/10 border-orange-500/20';
      case 'critical':
        return 'bg-red-500/10 border-red-500/20';
      default:
        return 'bg-slate-500/10 border-slate-500/20';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'low':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'medium':
        return <AlertCircle className="w-5 h-5 text-yellow-400" />;
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-orange-400" />;
      case 'critical':
        return <AlertTriangle className="w-5 h-5 text-red-400" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="text-slate-400">Loading threat analysis...</div>
        </div>
      </div>
    );
  }

  if (!threat) {
    return (
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="text-slate-400">Unable to load threat analysis</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border p-6 ${getRiskBgColor(threat.risk_level)}`}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">Threat Analysis</h2>
        <div className="flex items-center gap-2">
          {getRiskIcon(threat.risk_level)}
          <span className={`text-sm font-semibold capitalize ${getRiskColor(threat.risk_level)}`}>
            {threat.risk_level}
          </span>
        </div>
      </div>

      {/* Threat Score */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-slate-300">Threat Score</span>
          <span className={`text-2xl font-bold ${getRiskColor(threat.risk_level)}`}>
            {threat.threat_score}/10
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-700/50">
          <div
            className={`h-full rounded-full transition-all ${
              threat.risk_level === 'low'
                ? 'bg-green-500'
                : threat.risk_level === 'medium'
                  ? 'bg-yellow-500'
                  : threat.risk_level === 'high'
                    ? 'bg-orange-500'
                    : 'bg-red-500'
            }`}
            style={{ width: `${(threat.threat_score / 10) * 100}%` }}
          />
        </div>
      </div>

      {/* Findings */}
      <div className="mb-6">
        <h3 className="mb-3 text-sm font-semibold text-slate-200">Security Findings</h3>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Public Buckets:</span>
            <span className="font-medium text-slate-200">{threat.findings.public_buckets}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Unauthorized Regions:</span>
            <span className="font-medium text-slate-200">{threat.findings.unauthorized_regions}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Cost Spike:</span>
            <span className="font-medium text-slate-200">
              {threat.findings.high_cost_spike ? '감지됨' : '정상'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Anomalous API Activity:</span>
            <span className="font-medium text-slate-200">
              {threat.findings.anomalous_api_activity ? '감지됨' : '정상'}
            </span>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-200">Recommendations</h3>
        <div className="space-y-2">
          {threat.recommendations.map((rec, idx) => (
            <div key={idx} className="flex items-start gap-2 text-sm">
              <Zap className="mt-0.5 w-4 h-4 flex-shrink-0 text-yellow-500" />
              <span className="text-slate-300">{rec}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
