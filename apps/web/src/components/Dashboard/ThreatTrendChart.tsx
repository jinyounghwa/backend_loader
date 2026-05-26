'use client';

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart
} from 'recharts';
import { Clock, TrendingUp } from 'lucide-react';

interface HourlyData {
  hour: string;
  threats: number;
  avg_severity: number;
}

interface TrendData {
  hourly_breakdown: HourlyData[];
  daily_breakdown: any[];
  peak_hours: string[];
  safe_hours: string[];
  anomaly_hours: string[];
  trend: string;
  time_range: string;
}

export default function ThreatTrendChart() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TrendData | null>(null);
  const [accountId, setAccountId] = useState('');
  const [timeRange, setTimeRange] = useState('24h');

  const fetchTrends = async () => {
    if (!accountId) {
      setError('Please enter account ID');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `/api/guardian/ml/trends?account_id=${accountId}&time_range=${timeRange}`,
        { method: 'GET' }
      );

      if (!response.ok) throw new Error('Failed to fetch trends');

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (accountId) {
      const timer = setTimeout(fetchTrends, 500);
      return () => clearTimeout(timer);
    }
  }, [timeRange]);

  const chartData = data?.hourly_breakdown.map((item) => ({
    ...item,
    isPeakHour: data.peak_hours.includes(item.hour),
    isSafeHour: data.safe_hours.includes(item.hour),
    isAnomalyHour: data.anomaly_hours.includes(item.hour)
  })) || [];

  const getHourColor = (hour: string) => {
    if (data?.peak_hours.includes(hour)) return '#ef4444';
    if (data?.anomaly_hours.includes(hour)) return '#f59e0b';
    if (data?.safe_hours.includes(hour)) return '#10b981';
    return '#3b82f6';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Threat Trends</h2>
        <Clock className="w-6 h-6 text-indigo-500" />
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Enter account ID"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="24h">Last 24h</option>
          <option value="7d">Last 7d</option>
          <option value="30d">Last 30d</option>
        </select>
        <button
          onClick={fetchTrends}
          disabled={!accountId || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Loading...' : 'Analyze'}
        </button>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-red-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Peak Hours</p>
              <p className="text-lg font-mono text-red-600">{data.peak_hours.join(', ') || 'None'}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Safe Hours</p>
              <p className="text-lg font-mono text-green-600">{data.safe_hours.slice(0, 3).join(', ') || 'None'}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Anomaly Hours</p>
              <p className="text-lg font-mono text-amber-600">{data.anomaly_hours.join(', ') || 'None'}</p>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-4">Hourly Threat Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="threats"
                  fill="#3b82f6"
                  name="Threat Count"
                  radius={[4, 4, 0, 0]}
                />
                <Line
                  type="monotone"
                  dataKey="avg_severity"
                  stroke="#ef4444"
                  name="Avg Severity"
                  yAxisId="right"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold mb-4">Hour Analysis</h3>
            <div className="grid grid-cols-4 gap-2">
              {chartData.map((item) => (
                <div
                  key={item.hour}
                  className={`p-3 rounded-lg text-center ${
                    item.isPeakHour
                      ? 'bg-red-100 border border-red-300'
                      : item.isAnomalyHour
                      ? 'bg-amber-100 border border-amber-300'
                      : item.isSafeHour
                      ? 'bg-green-100 border border-green-300'
                      : 'bg-gray-100 border border-gray-300'
                  }`}
                >
                  <p className="text-xs font-mono text-gray-600">{item.hour}</p>
                  <p className="text-lg font-bold">
                    {item.threats}
                  </p>
                  <p className="text-xs text-gray-600">
                    severity: {item.avg_severity.toFixed(1)}
                  </p>
                  {item.isPeakHour && (
                    <p className="text-xs font-semibold text-red-600 mt-1">PEAK</p>
                  )}
                  {item.isAnomalyHour && (
                    <p className="text-xs font-semibold text-amber-600 mt-1">⚠️ ANOMALY</p>
                  )}
                  {item.isSafeHour && (
                    <p className="text-xs font-semibold text-green-600 mt-1">SAFE</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="text-center py-8 text-gray-500">
          Enter an account ID to view threat trends
        </div>
      )}
    </div>
  );
}
