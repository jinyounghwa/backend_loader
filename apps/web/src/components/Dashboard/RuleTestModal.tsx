'use client';

import { useState } from 'react';
import { X, Play, AlertCircle } from 'lucide-react';

interface TestResult {
  success: boolean;
  rule_id: string;
  total_logs: number;
  matched_logs: number;
  detected_threats: Array<{
    threat_id: string;
    rule_id: string;
    severity: number;
    message: string;
    evidence_count: number;
  }>;
  execution_time_ms: number;
  error_message?: string;
}

interface RuleTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  rule?: {
    rule_id: string;
    rule_type: string;
    condition: Record<string, any>;
    action: Record<string, any>;
    priority?: number;
  };
}

export function RuleTestModal({ isOpen, onClose, rule }: RuleTestModalProps) {
  const [testLogs, setTestLogs] = useState<string>('[\n  {\n    "event_type": "$connect",\n    "timestamp": "2026-05-23T10:00:00Z",\n    "account_id": "acc-1"\n  }\n]');
  const [accountId, setAccountId] = useState('acc-1');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTestRule = async () => {
    if (!rule) {
      setError('No rule provided');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      let logs: any[];
      try {
        logs = JSON.parse(testLogs);
      } catch (e) {
        throw new Error('Invalid JSON in test logs');
      }

      if (!Array.isArray(logs)) {
        throw new Error('Test logs must be an array');
      }

      const response = await fetch('/api/guardian/rules/test-run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rule,
          test_logs: logs,
          account_id: accountId,
        }),
      });

      const data: TestResult = await response.json();

      if (!response.ok) {
        setError(data.error_message || 'Failed to run test');
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg border border-slate-700 w-full max-w-3xl max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700 sticky top-0 bg-slate-900">
          <h2 className="text-xl font-bold text-white">
            규칙 테스트: {rule?.rule_type}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Rule Info */}
          {rule && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <p className="text-sm text-gray-300">
                <span className="font-semibold text-white">규칙 ID:</span> {rule.rule_id}
              </p>
              <p className="text-sm text-gray-300 mt-1">
                <span className="font-semibold text-white">우선순위:</span> {rule.priority || 5}
              </p>
            </div>
          )}

          {/* Account ID Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              계정 ID
            </label>
            <input
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              placeholder="acc-1"
            />
          </div>

          {/* Test Logs Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              샘플 로그 (JSON 배열)
            </label>
            <textarea
              value={testLogs}
              onChange={(e) => setTestLogs(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-500"
              rows={8}
              placeholder="[{\n  event_type: '$connect',\n  timestamp: '2026-05-23T10:00:00Z'\n}]"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-3 flex gap-2">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}

          {/* Test Button */}
          <button
            onClick={handleTestRule}
            disabled={isLoading || !rule}
            className="w-full px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" />
            {isLoading ? '테스트 실행 중...' : '테스트 실행'}
          </button>

          {/* Results */}
          {result && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
              <h3 className="font-semibold text-white">테스트 결과</h3>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-400">총 로그</p>
                  <p className="text-lg font-bold text-white">{result.total_logs}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">매칭된 로그</p>
                  <p className="text-lg font-bold text-amber-400">{result.matched_logs}</p>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-400">실행 시간</p>
                <p className="text-sm text-white">{result.execution_time_ms.toFixed(2)}ms</p>
              </div>

              {result.detected_threats.length > 0 && (
                <div className="bg-red-900/10 border border-red-700/30 rounded p-3">
                  <p className="text-sm font-semibold text-red-300 mb-2">
                    탐지된 위협 ({result.detected_threats.length})
                  </p>
                  {result.detected_threats.map((threat) => (
                    <div key={threat.threat_id} className="text-sm text-red-200 mt-1">
                      <p>심각도: {threat.severity}/10 - {threat.message}</p>
                    </div>
                  ))}
                </div>
              )}

              {result.matched_logs === 0 && (
                <div className="bg-green-900/10 border border-green-700/30 rounded p-3">
                  <p className="text-sm text-green-300">규칙과 매칭된 로그가 없습니다.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-6 border-t border-slate-700 sticky bottom-0 bg-slate-900">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
