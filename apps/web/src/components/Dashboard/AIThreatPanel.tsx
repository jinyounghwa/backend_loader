'use client';

import { memo } from 'react';
import { Brain, RefreshCw, AlertTriangle, Shield } from 'lucide-react';
import type { ThreatAnalysis } from '@/lib/hooks/useAIAnalysis';

interface AIThreatPanelProps {
  analysis: ThreatAnalysis | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

function AIThreatPanel({ analysis, loading, error, onRefresh }: AIThreatPanelProps) {
  if (!analysis && !error && !loading) {
    return (
      <div className="p-4 rounded-lg border bg-slate-500/10 border-slate-500/20 text-center">
        <Brain className="w-8 h-8 text-slate-400 mx-auto mb-2 opacity-50" />
        <p className="text-sm text-slate-400">AI 위협 분석 대기 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg border bg-red-500/10 border-red-500/20">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <span className="text-sm font-medium text-red-400">분석 실패</span>
        </div>
        <p className="text-xs text-red-300">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 rounded-lg border bg-blue-500/10 border-blue-500/20">
        <div className="flex items-center gap-2 mb-2">
          <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
          <span className="text-sm font-medium text-blue-400">분석 중...</span>
        </div>
        <p className="text-xs text-blue-300">Gemini AI가 위협을 분석하고 있습니다</p>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  const severityColors: Record<string, { bg: string; border: string; text: string; badge: string }> = {
    Critical: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      text: 'text-red-400',
      badge: 'bg-red-500 text-red-50',
    },
    High: {
      bg: 'bg-orange-500/10',
      border: 'border-orange-500/20',
      text: 'text-orange-400',
      badge: 'bg-orange-500 text-orange-50',
    },
    Medium: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      text: 'text-amber-400',
      badge: 'bg-amber-500 text-amber-50',
    },
    Low: {
      bg: 'bg-green-500/10',
      border: 'border-green-500/20',
      text: 'text-green-400',
      badge: 'bg-green-500 text-green-50',
    },
  };

  const colors = severityColors[analysis.severity] || severityColors.Medium;

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className={`w-5 h-5 ${colors.text}`} />
          <span className="text-sm font-medium text-slate-300">AI 위협 분석</span>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1 hover:bg-slate-700/50 rounded transition-colors disabled:opacity-50"
          title="분석 새로고침"
        >
          <RefreshCw className="w-4 h-4 text-slate-400 hover:text-slate-300" />
        </button>
      </div>

      <div className="mb-3">
        <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${colors.badge} mb-2`}>
          {analysis.severity} 위협
        </div>
        <p className={`text-sm ${colors.text} font-semibold`}>{analysis.rootCause}</p>
      </div>

      <div className="space-y-3">
        <div>
          <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            즉시 조치 항목
          </h4>
          <ul className="space-y-1">
            {analysis.remediationSteps.map((step, i) => (
              <li key={i} className="text-xs text-slate-400">
                • {step}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-semibold text-slate-300 mb-2">예방 권고사항</h4>
          <ul className="space-y-1">
            {analysis.preventionTips.map((tip, i) => (
              <li key={i} className="text-xs text-slate-400">
                • {tip}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default memo(AIThreatPanel);
