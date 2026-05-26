'use client';

import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts';
import { Zap, Activity } from 'lucide-react';

interface Threat {
  threat_id: string;
  severity: number;
  account_risk_score: number;
  event_frequency: number;
  resource_impact_count: number;
  response_time_seconds: number;
  remediation_success_rate: number;
}

interface ClusterData {
  id: string;
  threats: string[];
  threat_count: number;
  cohesion: number;
  avg_severity: number;
}

interface ClusteringResponse {
  clusters: ClusterData[];
  silhouette_score: number;
  cluster_count: number;
  threat_count: number;
}

export default function AnomalyClusterPanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClusteringResponse | null>(null);
  const [threats, setThreats] = useState<Threat[]>([]);
  const [nClusters, setNClusters] = useState(5);
  const [threatInput, setThreatInput] = useState('');

  const handleAddThreat = () => {
    try {
      const threat = JSON.parse(threatInput);
      setThreats([...threats, threat]);
      setThreatInput('');
    } catch (e) {
      setError('Invalid JSON format');
    }
  };

  const handleCluster = async () => {
    if (threats.length === 0) {
      setError('Please add at least one threat');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/guardian/ml/cluster', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          threats,
          n_clusters: nClusters
        })
      });

      if (!response.ok) throw new Error('Failed to cluster threats');

      const data = await response.json();
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const clusterChartData = result?.clusters.map((cluster, idx) => ({
    name: cluster.id,
    count: cluster.threat_count,
    severity: cluster.avg_severity,
    cohesion: cluster.cohesion
  })) || [];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Anomaly Clustering</h2>
        <Zap className="w-6 h-6 text-yellow-500" />
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Number of Clusters</label>
          <input
            type="number"
            min="2"
            max="20"
            value={nClusters}
            onChange={(e) => setNClusters(parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Add Threat (JSON)</label>
          <div className="flex gap-2">
            <textarea
              value={threatInput}
              onChange={(e) => setThreatInput(e.target.value)}
              placeholder='{"threat_id": "t1", "severity": 8, "account_risk_score": 0.8, ...}'
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm h-20"
            />
            <button
              onClick={handleAddThreat}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Add
            </button>
          </div>
          {threats.length > 0 && (
            <p className="text-sm text-gray-600 mt-2">{threats.length} threat(s) added</p>
          )}
        </div>

        <button
          onClick={handleCluster}
          disabled={threats.length === 0 || loading}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
        >
          {loading ? 'Clustering...' : 'Perform Clustering'}
        </button>
      </div>

      {result && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Clusters Created</p>
              <p className="text-2xl font-bold text-blue-600">{result.cluster_count}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Silhouette Score</p>
              <p className="text-2xl font-bold text-purple-600">
                {result.silhouette_score.toFixed(2)}
              </p>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-4">Cluster Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={clusterChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#3b82f6" name="Threat Count" />
                <Bar dataKey="severity" fill="#ef4444" name="Avg Severity" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-4">
            {result.clusters.map((cluster) => (
              <div key={cluster.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-600" />
                    {cluster.id}
                  </h4>
                  <span className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded-full">
                    {cluster.threat_count} threats
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="text-sm">
                    <p className="text-gray-600">Avg Severity</p>
                    <p className="font-semibold text-lg">{cluster.avg_severity.toFixed(1)}</p>
                  </div>
                  <div className="text-sm">
                    <p className="text-gray-600">Cohesion</p>
                    <p className="font-semibold text-lg">{cluster.cohesion.toFixed(2)}</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 mb-2">Members:</p>
                  <div className="flex flex-wrap gap-2">
                    {cluster.threats.map((threatId) => (
                      <span key={threatId} className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {threatId}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!result && threats.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">
          Add threats and click Perform Clustering to group similar threats
        </div>
      )}
    </div>
  );
}
