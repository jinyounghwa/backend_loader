'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import GuardianAutoRemediation from '@/components/Dashboard/GuardianAutoRemediation';
import GuardianThreatAnalysis from '@/components/Dashboard/GuardianThreatAnalysis';

export default function RemediationPage() {
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const handleRefresh = async () => {
    // 새로고침 로직
    setLastRefresh(new Date());
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              Back to Dashboard
            </Link>
          </div>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-700"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Auto-Remediation Center</h1>
          <p className="mt-2 text-slate-400">Configure automatic threat response rules and view remediation history</p>
        </div>

        {lastRefresh && (
          <div className="text-sm text-slate-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </div>
        )}

        {/* Threat Analysis Overview */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <GuardianThreatAnalysis />
          </div>
          <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
            <h3 className="mb-4 text-lg font-semibold text-slate-100">Quick Stats</h3>
            <div className="space-y-4">
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  Total Rules
                </div>
                <div className="mt-1 text-2xl font-bold text-slate-100">3</div>
              </div>
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  Auto-Enabled
                </div>
                <div className="mt-1 text-2xl font-bold text-green-400">2</div>
              </div>
              <div className="rounded border border-slate-700/30 bg-slate-800/30 p-4">
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                  Recent Actions
                </div>
                <div className="mt-1 text-2xl font-bold text-slate-100">5</div>
              </div>
            </div>
          </div>
        </div>

        {/* Auto-Remediation Rules and History */}
        <GuardianAutoRemediation />
      </div>
    </div>
  );
}
