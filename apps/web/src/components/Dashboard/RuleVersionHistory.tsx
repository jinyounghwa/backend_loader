'use client';

import { useState, useEffect } from 'react';
import { RotateCcw, AlertCircle, Clock } from 'lucide-react';
import { SecurityRule } from '@/lib/hooks/useSecurityRules';

interface RuleVersion {
  version_id: string;
  version_number: number;
  created_at: string;
  created_by?: string;
  change_reason?: string;
  rule_content?: Record<string, any>;
}

interface RuleVersionHistoryProps {
  rule: SecurityRule;
  onRollbackSuccess?: (version: RuleVersion) => void;
}

export function RuleVersionHistory({ rule, onRollbackSuccess }: RuleVersionHistoryProps) {
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);

  // Load version history
  useEffect(() => {
    loadVersionHistory();
  }, [rule.rule_id]);

  const loadVersionHistory = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/guardian/rules/${rule.rule_id}/versions`
      );

      if (response.ok) {
        const data = await response.json();
        setVersions(data.versions || []);
      } else {
        console.warn('Failed to load version history');
        setVersions([]);
      }
    } catch (err) {
      console.error('Error loading version history:', err);
      setVersions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRollback = async (versionId: string) => {
    if (!confirm('이전 버전으로 롤백하시겠습니까?')) {
      return;
    }

    setIsRollingBack(versionId);
    setError(null);

    try {
      const response = await fetch(
        `/api/guardian/rules/${rule.rule_id}/rollback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            version_id: versionId,
            rolled_back_by: 'user',
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_message || 'Rollback failed');
      }

      const data = await response.json();

      // Create version object for callback
      const targetVersion = versions.find(v => v.version_id === versionId);
      if (targetVersion) {
        onRollbackSuccess?.(targetVersion);
      }

      // Reload version history to show new version
      await loadVersionHistory();

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsRollingBack(null);
    }
  };

  const formatDate = (isoString: string): string => {
    try {
      return new Date(isoString).toLocaleString('ko-KR');
    } catch {
      return isoString;
    }
  };

  const getVersionLabel = (versionNumber: number): string => {
    return `v${versionNumber}`;
  };

  return (
    <div className="space-y-4">
      {/* Version Stats */}
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-sm text-gray-400 mb-1">총 버전</div>
        <div className="text-2xl font-bold text-white">{versions.length}</div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Version History Timeline */}
      <div className="space-y-3">
        <h3 className="text-lg font-bold text-white">버전 이력</h3>

        {isLoading ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            로드 중...
          </div>
        ) : versions.length === 0 ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            버전 이력이 없습니다
          </div>
        ) : (
          <div className="space-y-2">
            {versions.map((version, index) => (
              <div
                key={version.version_id}
                className={`p-4 rounded-lg border transition-colors ${
                  selectedVersion === version.version_id
                    ? 'bg-slate-700/50 border-blue-500/50'
                    : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                } cursor-pointer`}
                onClick={() => setSelectedVersion(version.version_id)}
              >
                {/* Version Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 font-bold text-sm">
                      {getVersionLabel(version.version_number)}
                    </div>
                    <div>
                      <div className="font-semibold text-white">
                        {version.change_reason || '규칙 업데이트'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {version.created_by || 'system'} · {formatDate(version.created_at)}
                      </div>
                    </div>
                  </div>

                  {/* Rollback Button (only for non-latest versions) */}
                  {index > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRollback(version.version_id);
                      }}
                      disabled={isRollingBack === version.version_id}
                      className="flex items-center gap-2 px-3 py-1 text-sm bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      {isRollingBack === version.version_id ? '롤백 중...' : '롤백'}
                    </button>
                  )}

                  {index === 0 && (
                    <span className="px-3 py-1 text-xs bg-green-500/20 text-green-400 rounded font-semibold">
                      현재
                    </span>
                  )}
                </div>

                {/* Version Details */}
                {selectedVersion === version.version_id && (
                  <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
                    <div className="text-xs space-y-1">
                      <div className="text-gray-400">
                        버전 ID: <span className="text-gray-300 font-mono">{version.version_id.slice(0, 12)}...</span>
                      </div>
                      {version.rule_content && (
                        <div className="text-gray-400">
                          규칙 타입:{' '}
                          <span className="text-gray-300">
                            {version.rule_content.rule_type || 'Unknown'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 text-xs text-gray-400">
        <div className="flex items-start gap-2">
          <Clock className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div>
            이전 버전을 선택하고 "롤백" 버튼을 클릭하면 해당 버전으로 되돌릴 수 있습니다.
            모든 변경 사항은 감사 로그에 기록됩니다.
          </div>
        </div>
      </div>
    </div>
  );
}
