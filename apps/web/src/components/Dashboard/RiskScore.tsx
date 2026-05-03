'use client';

import { AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react';

interface RiskScoreProps {
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  totalIssues: number;
}

export default function RiskScore({ criticalCount, highCount, mediumCount, totalIssues }: RiskScoreProps) {
  const riskScore = totalIssues === 0 ? 0 : Math.round((criticalCount * 10 + highCount * 5 + mediumCount * 2) / Math.max(1, totalIssues));

  let riskLevel = 'Low';
  let riskColor = 'text-green-400';
  let bgColor = 'bg-green-500/10';
  let borderColor = 'border-green-500/20';
  let Icon = CheckCircle;

  if (riskScore >= 50) {
    riskLevel = 'Critical';
    riskColor = 'text-red-400';
    bgColor = 'bg-red-500/10';
    borderColor = 'border-red-500/20';
    Icon = AlertTriangle;
  } else if (riskScore >= 20) {
    riskLevel = 'Medium';
    riskColor = 'text-amber-400';
    bgColor = 'bg-amber-500/10';
    borderColor = 'border-amber-500/20';
    Icon = AlertCircle;
  }

  return (
    <div className={`p-4 rounded-lg border ${bgColor} ${borderColor}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-sm font-medium ${riskColor}`}>Risk Assessment</span>
        <Icon className={`w-5 h-5 ${riskColor}`} />
      </div>

      <div className={`text-3xl font-bold ${riskColor} mb-2`}>{riskScore}</div>

      <div className={`text-sm ${riskColor} font-semibold mb-3`}>{riskLevel} Risk</div>

      <div className="space-y-1 text-xs text-slate-400">
        <div>
          <span className="text-red-400 font-medium">{criticalCount}</span> Critical
        </div>
        <div>
          <span className="text-amber-400 font-medium">{highCount}</span> High
        </div>
        <div>
          <span className="text-blue-400 font-medium">{mediumCount}</span> Medium
        </div>
      </div>
    </div>
  );
}
