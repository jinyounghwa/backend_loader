'use client';

import { useState } from 'react';
import { useSecurityRules, SecurityRule } from '@/lib/hooks/useSecurityRules';
import { Trash2, Edit, AlertCircle, CheckCircle } from 'lucide-react';

interface RulesListProps {
  accountId?: string;
  onEditRule?: (rule: SecurityRule) => void;
}

export function RulesList({ accountId, onEditRule }: RulesListProps) {
  const { rules, isLoading, error, updateRule, deleteRule } = useSecurityRules({
    account_id: accountId,
    auto_refresh: true,
  });

  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null);

  const handleToggleEnabled = async (rule: SecurityRule) => {
    try {
      await updateRule(rule.rule_id, { enabled: !rule.enabled });
    } catch (err) {
      console.error('Failed to toggle rule:', err);
    }
  };

  const handleDelete = async (rule_id: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) {
      return;
    }

    setDeletingRuleId(rule_id);
    try {
      await deleteRule(rule_id);
    } catch (err) {
      console.error('Failed to delete rule:', err);
    } finally {
      setDeletingRuleId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-gray-400">로드 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
        <div className="text-center text-red-400">규칙 로드 실패: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">보안 규칙 ({rules.length})</h3>
      </div>

      {rules.length === 0 ? (
        <div className="p-8 bg-slate-800 rounded-lg border border-slate-700 text-center">
          <div className="text-gray-400">등록된 규칙이 없습니다</div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">규칙</th>
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">타입</th>
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">우선순위</th>
                <th className="px-4 py-3 text-left text-gray-400 font-semibold">계정</th>
                <th className="px-4 py-3 text-center text-gray-400 font-semibold">활성화</th>
                <th className="px-4 py-3 text-right text-gray-400 font-semibold">작업</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr
                  key={rule.rule_id}
                  className="border-b border-slate-700 hover:bg-slate-700/50 transition-colors"
                >
                  <td className="px-4 py-3 text-white font-mono text-xs">{rule.rule_id}</td>
                  <td className="px-4 py-3 text-gray-300">{rule.rule_type}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-white font-bold text-xs ${
                      rule.priority >= 8 ? 'bg-red-600' :
                      rule.priority >= 6 ? 'bg-orange-600' :
                      rule.priority >= 4 ? 'bg-yellow-600' :
                      'bg-blue-600'
                    }`}>
                      {rule.priority}/10
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300 font-mono text-xs">
                    {rule.account_id || '모든 계정'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleToggleEnabled(rule)}
                      className="inline-flex items-center justify-center transition-colors hover:opacity-75"
                      title={rule.enabled ? '비활성화' : '활성화'}
                    >
                      {rule.enabled ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-gray-500" />
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onEditRule?.(rule)}
                        className="p-2 hover:bg-slate-600 rounded transition-colors text-blue-400 hover:text-blue-300"
                        title="편집"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(rule.rule_id)}
                        disabled={deletingRuleId === rule.rule_id}
                        className="p-2 hover:bg-slate-600 rounded transition-colors text-red-400 hover:text-red-300 disabled:opacity-50"
                        title="삭제"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
