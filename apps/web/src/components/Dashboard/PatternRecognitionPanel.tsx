'use client';

import React, { useState } from 'react';
import { Eye, Target } from 'lucide-react';

interface Pattern {
  id: string;
  sequence: string[];
  support: number;
  confidence: number;
  lift: number;
  occurrences: number;
}

interface PatternResponse {
  patterns: Pattern[];
  total_patterns: number;
  threat_count: number;
}

export default function PatternRecognitionPanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PatternResponse | null>(null);
  const [threatsInput, setThreatsInput] = useState('');
  const [minSupport, setMinSupport] = useState(0.3);

  const handleIdentifyPatterns = async () => {
    try {
      const threats = threatsInput
        .split('\n')
        .map((line) => {
          try {
            return JSON.parse(line.trim());
          } catch {
            return null;
          }
        })
        .filter(Boolean);

      if (threats.length === 0) {
        setError('Please enter valid threat JSON objects');
        return;
      }

      setLoading(true);
      const response = await fetch('/api/guardian/ml/patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          threats,
          min_support: minSupport
        })
      });

      if (!response.ok) throw new Error('Failed to identify patterns');

      const data = await response.json();
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.9) return 'text-green-600 bg-green-50';
    if (confidence > 0.7) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Pattern Recognition</h2>
        <Target className="w-6 h-6 text-green-500" />
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Threat Sequence (JSON, one per line)
          </label>
          <textarea
            value={threatsInput}
            onChange={(e) => setThreatsInput(e.target.value)}
            placeholder='{"threat_type": "Unknown Region", "timestamp": "2026-05-26T00:00:00"}&#10;{"threat_type": "Unauthorized SSH", "timestamp": "2026-05-26T01:00:00"}'
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm h-32"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Minimum Support: {minSupport.toFixed(2)}
          </label>
          <input
            type="range"
            min="0.1"
            max="0.9"
            step="0.05"
            value={minSupport}
            onChange={(e) => setMinSupport(parseFloat(e.target.value))}
            className="w-full"
          />
          <p className="text-xs text-gray-600 mt-1">
            Patterns appearing in at least {(minSupport * 100).toFixed(0)}% of sequences
          </p>
        </div>

        <button
          onClick={handleIdentifyPatterns}
          disabled={!threatsInput.trim() || loading}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
        >
          {loading ? 'Analyzing...' : 'Identify Patterns'}
        </button>
      </div>

      {result && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Patterns Found</p>
              <p className="text-2xl font-bold text-blue-600">{result.total_patterns}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Threats Analyzed</p>
              <p className="text-2xl font-bold text-purple-600">{result.threat_count}</p>
            </div>
          </div>

          {result.patterns.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No patterns found with the current minimum support threshold
            </div>
          ) : (
            <div className="space-y-4">
              {result.patterns.map((pattern) => (
                <div
                  key={pattern.id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-semibold flex items-center gap-2">
                        <Eye className="w-4 h-4 text-blue-600" />
                        {pattern.id}
                      </h4>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {pattern.sequence.map((threat, idx) => (
                          <span key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                            {threat}
                            {idx < pattern.sequence.length - 1 && (
                              <span className="ml-1 text-gray-400">→</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                    <span className="text-sm font-mono bg-gray-100 px-3 py-1 rounded">
                      {pattern.occurrences}x
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-3">
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <p className="text-xs text-gray-600 mb-1">Support</p>
                      <p className="font-semibold text-blue-600">
                        {(pattern.support * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div className={`text-center p-2 rounded ${getConfidenceColor(pattern.confidence)}`}>
                      <p className="text-xs text-gray-600 mb-1">Confidence</p>
                      <p className="font-semibold">
                        {(pattern.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div className="text-center p-2 bg-green-50 rounded">
                      <p className="text-xs text-gray-600 mb-1">Lift</p>
                      <p className="font-semibold text-green-600">
                        {pattern.lift.toFixed(2)}x
                      </p>
                    </div>
                    <div className="text-center p-2 bg-purple-50 rounded">
                      <p className="text-xs text-gray-600 mb-1">Occurrences</p>
                      <p className="font-semibold text-purple-600">
                        {pattern.occurrences}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                    <strong>Insight:</strong> This {pattern.sequence.length}-step pattern occurs{' '}
                    {(pattern.support * 100).toFixed(0)}% of the time with{' '}
                    {(pattern.confidence * 100).toFixed(0)}% probability.
                    {pattern.lift > 1.5 && (
                      <span> Strong correlation detected ({pattern.lift.toFixed(1)}x lift).</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!result && !loading && (
        <div className="text-center py-8 text-gray-500">
          Enter threat sequences to identify repeating attack patterns
        </div>
      )}
    </div>
  );
}
