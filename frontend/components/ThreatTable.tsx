/**
 * ThreatTable Component
 * Displays real-time threat table with filtering and sorting
 */

'use client';

import React, { useState, useEffect } from 'react';

interface Threat {
  id: string;
  type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  timestamp: string;
  resource_id?: string;
  description?: string;
}

interface ThreatTableProps {
  threats: Threat[];
  onRowClick?: (threat: Threat) => void;
  onRefresh?: () => Promise<void>;
}

const SEVERITY_COLORS = {
  CRITICAL: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-900' },
  HIGH: { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-900' },
  MEDIUM: { bg: 'bg-yellow-50', border: 'border-yellow-300', text: 'text-yellow-900' },
  LOW: { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-900' }
};

export function ThreatTable({ threats, onRowClick, onRefresh }: ThreatTableProps) {
  const [sortBy, setSortBy] = useState<'severity' | 'timestamp'>('severity');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Sort threats
  const sortedThreats = React.useMemo(() => {
    let sorted = [...threats];

    if (sortBy === 'severity') {
      const severityOrder = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      sorted.sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity]);
    } else if (sortBy === 'timestamp') {
      sorted.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    }

    // Filter by severity
    if (filterSeverity) {
      sorted = sorted.filter(t => t.severity === filterSeverity);
    }

    return sorted;
  }, [threats, sortBy, filterSeverity]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh?.();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-4">
          {/* Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-2 border rounded-lg"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Sort Options */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 border rounded-lg"
          >
            <option value="severity">Sort by Severity</option>
            <option value="timestamp">Sort by Time</option>
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
          aria-label="Refresh threats"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">ID</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Type</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Severity</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Resource</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Time</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Description</th>
            </tr>
          </thead>
          <tbody>
            {sortedThreats.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No threats detected
                </td>
              </tr>
            ) : (
              sortedThreats.map((threat) => {
                const colors = SEVERITY_COLORS[threat.severity];
                return (
                  <tr
                    key={threat.id}
                    onClick={() => onRowClick?.(threat)}
                    className={`border-b hover:bg-gray-50 cursor-pointer ${colors.bg}`}
                  >
                    <td className="px-4 py-3 text-sm font-mono">{threat.id}</td>
                    <td className="px-4 py-3 text-sm">{threat.type}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`inline-block px-2 py-1 rounded font-semibold ${colors.text}`}>
                        {threat.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">{threat.resource_id || '-'}</td>
                    <td className="px-4 py-3 text-sm">{formatTime(threat.timestamp)}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{threat.description || '-'}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="text-sm text-gray-600">
        Showing {sortedThreats.length} of {threats.length} threats
      </div>
    </div>
  );
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
