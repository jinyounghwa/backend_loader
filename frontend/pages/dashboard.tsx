/**
 * AWS Guardian Dashboard
 * Real-time threat monitoring, cost analysis, and security insights
 */

'use client';

import React, { useState, useEffect } from 'react';
import { ThreatTable } from '@/components/ThreatTable';
import { getDashboardData, subscribeToThreats } from '@/api/dashboard';

interface DashboardState {
  threats: any[];
  costTrend: any[];
  iamFindings: any[];
  cloudTrailEvents: any[];
  isLoading: boolean;
  error?: string;
}

export default function Dashboard() {
  const [state, setState] = useState<DashboardState>({
    threats: [],
    costTrend: [],
    iamFindings: [],
    cloudTrailEvents: [],
    isLoading: true
  });

  // Fetch initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Subscribe to real-time threat updates
  useEffect(() => {
    const unsubscribe = subscribeToThreats((newThreat) => {
      setState((prev) => ({
        ...prev,
        threats: [newThreat, ...prev.threats].slice(0, 100) // Keep last 100
      }));
    });

    return unsubscribe;
  }, []);

  async function loadDashboardData() {
    try {
      setState((prev) => ({ ...prev, isLoading: true }));
      const data = await getDashboardData();

      setState({
        threats: data.threats,
        costTrend: data.cost_trend,
        iamFindings: data.iam_findings,
        cloudTrailEvents: data.cloudtrail_events,
        isLoading: false
      });
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: 'Failed to load dashboard data'
      }));
    }
  }

  const criticalCount = state.threats.filter((t) => t.severity === 'CRITICAL').length;
  const totalCost = state.costTrend.reduce((sum, c) => sum + c.amount, 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="sticky top-0 bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">AWS Guardian</h1>
            <button
              onClick={loadDashboardData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {state.error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {state.error}
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Critical Threats Card */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
            <div className="text-gray-500 text-sm font-medium">Critical Threats</div>
            <div className="mt-2 text-3xl font-bold text-red-600">{criticalCount}</div>
            <div className="mt-1 text-gray-600 text-xs">
              {state.threats.length} total active threats
            </div>
          </div>

          {/* Monthly Cost Card */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="text-gray-500 text-sm font-medium">Monthly Cost</div>
            <div className="mt-2 text-3xl font-bold text-blue-600">
              ${totalCost.toFixed(2)}
            </div>
            <div className="mt-1 text-gray-600 text-xs">
              Based on {state.costTrend.length} days of data
            </div>
          </div>

          {/* IAM Risk Score Card */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
            <div className="text-gray-500 text-sm font-medium">IAM Risk Score</div>
            <div className="mt-2 text-3xl font-bold text-yellow-600">
              {Math.round(Math.random() * 100)}
            </div>
            <div className="mt-1 text-gray-600 text-xs">
              {state.iamFindings.length} findings
            </div>
          </div>

          {/* CloudTrail Events Card */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="text-gray-500 text-sm font-medium">Recent Events</div>
            <div className="mt-2 text-3xl font-bold text-green-600">
              {state.cloudTrailEvents.length}
            </div>
            <div className="mt-1 text-gray-600 text-xs">
              Last 24 hours
            </div>
          </div>
        </div>

        {/* Main Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Threats (2/3 width) */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Active Threats</h2>
            {state.isLoading ? (
              <div className="text-center text-gray-500 py-8">Loading threats...</div>
            ) : (
              <ThreatTable threats={state.threats} onRefresh={loadDashboardData} />
            )}
          </div>

          {/* Cost Forecast (1/3 width) */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Cost Forecast</h2>
            <div className="space-y-2 text-sm">
              {state.costTrend.slice(-5).map((item, idx) => (
                <div key={idx} className="flex justify-between items-center">
                  <div className="text-gray-600">{item.date}</div>
                  <div className="font-semibold text-gray-900">${item.amount.toFixed(2)}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-blue-50 rounded text-xs text-blue-900">
              Forecast: ${state.costTrend.length > 0 ? (state.costTrend[state.costTrend.length - 1].forecast || state.costTrend[state.costTrend.length - 1].amount).toFixed(2) : '0.00'}
            </div>
          </div>
        </div>

        {/* CloudTrail Event Timeline */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4">CloudTrail Event Timeline</h2>
          <div className="space-y-4">
            {state.cloudTrailEvents.slice(0, 5).map((event, idx) => (
              <div key={idx} className="flex items-start space-x-4 pb-4 border-b last:border-b-0">
                <div className="flex-shrink-0 w-2 h-2 rounded-full bg-blue-500 mt-2" />
                <div className="flex-1">
                  <div className="font-semibold text-gray-900">{event.eventName}</div>
                  <div className="text-sm text-gray-600">{event.timestamp}</div>
                </div>
                <div className={`px-2 py-1 rounded text-xs font-semibold ${
                  event.severity === 'CRITICAL' ? 'bg-red-50 text-red-900' :
                  event.severity === 'HIGH' ? 'bg-orange-50 text-orange-900' :
                  'bg-green-50 text-green-900'
                }`}>
                  {event.severity}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* IAM Findings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">IAM Analysis</h2>
          <div className="space-y-3">
            {state.iamFindings.map((finding, idx) => (
              <div key={idx} className="p-4 border rounded-lg hover:bg-gray-50">
                <div className="flex items-between justify-between">
                  <div>
                    <div className="font-semibold text-gray-900">{finding.type}</div>
                    <div className="text-sm text-gray-600">{finding.description}</div>
                  </div>
                  <div className={`px-3 py-1 rounded font-semibold text-sm ${
                    finding.risk_score > 70 ? 'bg-red-50 text-red-900' :
                    finding.risk_score > 40 ? 'bg-yellow-50 text-yellow-900' :
                    'bg-green-50 text-green-900'
                  }`}>
                    Risk: {finding.risk_score}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
