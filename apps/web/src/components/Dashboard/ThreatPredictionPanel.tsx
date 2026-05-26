'use client';

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';

interface Prediction {
  date: string;
  expected_threats: number;
  confidence: number;
}

interface ThreatPredictionData {
  predictions: Prediction[];
  trend: 'increasing' | 'stable' | 'decreasing';
  anomaly_score: number;
  model_accuracy: number;
}

export default function ThreatPredictionPanel() {
  const [data, setData] = useState<ThreatPredictionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accountId, setAccountId] = useState('');

  useEffect(() => {
    if (accountId) {
      fetchPredictions();
    }
  }, [accountId]);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/guardian/ml/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: accountId,
          days_ahead: 7
        })
      });

      if (!response.ok) throw new Error('Failed to fetch predictions');

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = () => {
    if (!data) return null;
    switch (data.trend) {
      case 'increasing':
        return <TrendingUp className="text-red-500" />;
      case 'stable':
        return <CheckCircle className="text-green-500" />;
      case 'decreasing':
        return <TrendingUp className="text-blue-500 rotate-180" />;
    }
  };

  const getTrendColor = () => {
    if (!data) return 'text-gray-500';
    switch (data.trend) {
      case 'increasing':
        return 'text-red-600';
      case 'stable':
        return 'text-green-600';
      case 'decreasing':
        return 'text-blue-600';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Threat Predictions (7-Day)</h2>
        {data && getTrendIcon()}
      </div>

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Enter account ID"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={fetchPredictions}
          disabled={!accountId || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Loading...' : 'Predict'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Trend</p>
              <p className={`text-xl font-bold capitalize ${getTrendColor()}`}>
                {data.trend}
              </p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Model Accuracy</p>
              <p className="text-xl font-bold text-purple-600">
                {(data.model_accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Anomaly Score</p>
              <p className="text-xl font-bold text-orange-600">
                {(data.anomaly_score * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Avg Confidence</p>
              <p className="text-xl font-bold text-green-600">
                {(data.predictions.reduce((sum, p) => sum + p.confidence, 0) / data.predictions.length * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data.predictions}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                />
                <YAxis />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }}
                  formatter={(value: any) => {
                    if (typeof value === 'number' && value < 1) {
                      return `${(value * 100).toFixed(0)}%`;
                    }
                    return value.toFixed(2);
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="expected_threats"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="Expected Threats"
                />
                <Line
                  type="monotone"
                  dataKey="confidence"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Confidence"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-4">Detailed Predictions</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Date</th>
                    <th className="px-4 py-2 text-right">Expected Threats</th>
                    <th className="px-4 py-2 text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {data.predictions.map((pred, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="px-4 py-2">{pred.date}</td>
                      <td className="px-4 py-2 text-right font-mono">
                        {pred.expected_threats.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className={`px-2 py-1 rounded text-white text-xs font-bold ${
                          pred.confidence > 0.9 ? 'bg-green-500' :
                          pred.confidence > 0.7 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}>
                          {(pred.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!data && !loading && !error && (
        <div className="text-center py-8 text-gray-500">
          Enter an account ID and click Predict to see threat forecasts
        </div>
      )}
    </div>
  );
}
