'use client';

import { useState, useEffect } from 'react';
import { useSecurityRules, SecurityRule } from '@/lib/hooks/useSecurityRules';
import { X } from 'lucide-react';

interface RuleEditorProps {
  isOpen: boolean;
  rule?: SecurityRule | null;
  onClose: () => void;
}

type RuleType = 'connection_spike' | 'auth_failure' | 'unknown_region' | 'public_bucket';

const RULE_TYPES: { value: RuleType; label: string }[] = [
  { value: 'connection_spike', label: '연결 급증' },
  { value: 'auth_failure', label: '인증 실패' },
  { value: 'unknown_region', label: '미알려 리전' },
  { value: 'public_bucket', label: '공개 버킷' },
];

export function RuleEditor({ isOpen, rule, onClose }: RuleEditorProps) {
  const { createRule, updateRule } = useSecurityRules();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState<Partial<SecurityRule>>({
    rule_type: 'connection_spike',
    condition: { threshold: 10, window_minutes: 5 },
    action: { notify: ['telegram', 'discord'] },
    priority: 5,
    account_id: undefined,
    enabled: true,
  });

  useEffect(() => {
    if (rule) {
      setFormData(rule);
    } else {
      setFormData({
        rule_type: 'connection_spike',
        condition: { threshold: 10, window_minutes: 5 },
        action: { notify: ['telegram', 'discord'] },
        priority: 5,
        account_id: undefined,
        enabled: true,
      });
    }
  }, [rule, isOpen]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleConditionChange = (key: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      condition: {
        ...((prev.condition as Record<string, any>) || {}),
        [key]: value,
      },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (rule?.rule_id) {
        // Update existing rule
        await updateRule(rule.rule_id, formData);
      } else {
        // Create new rule
        const newRule = {
          rule_type: formData.rule_type!,
          condition: formData.condition!,
          action: formData.action!,
          priority: formData.priority!,
          account_id: formData.account_id,
          enabled: formData.enabled !== false,
        };
        await createRule(newRule);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save rule:', error);
      alert(`규칙 저장 실패: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg border border-slate-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">
            {rule ? '규칙 편집' : '새 규칙 생성'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded transition-colors text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Rule Type */}
          <div>
            <label className="block text-sm font-bold text-white mb-2">
              규칙 타입
            </label>
            <select
              value={formData.rule_type || 'connection_spike'}
              onChange={(e) => handleChange('rule_type', e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 rounded border border-slate-600 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {RULE_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Condition */}
          <div>
            <label className="block text-sm font-bold text-white mb-2">
              감지 조건
            </label>
            <div className="space-y-2 p-4 bg-slate-700/50 rounded border border-slate-600">
              {formData.rule_type === 'connection_spike' && (
                <>
                  <div>
                    <label className="text-xs text-gray-400">임계값</label>
                    <input
                      type="number"
                      value={(formData.condition as any)?.threshold || 10}
                      onChange={(e) => handleConditionChange('threshold', parseInt(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-700 rounded border border-slate-600 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400">윈도우 (분)</label>
                    <input
                      type="number"
                      value={(formData.condition as any)?.window_minutes || 5}
                      onChange={(e) => handleConditionChange('window_minutes', parseInt(e.target.value))}
                      className="w-full px-3 py-2 bg-slate-700 rounded border border-slate-600 text-white text-sm"
                    />
                  </div>
                </>
              )}
              {formData.rule_type === 'auth_failure' && (
                <div>
                  <label className="text-xs text-gray-400">임계값</label>
                  <input
                    type="number"
                    value={(formData.condition as any)?.threshold || 5}
                    onChange={(e) => handleConditionChange('threshold', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-700 rounded border border-slate-600 text-white text-sm"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-bold text-white mb-2">
              우선순위 (1-10)
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={formData.priority || 5}
              onChange={(e) => handleChange('priority', parseInt(e.target.value))}
              className="w-full"
            />
            <div className="mt-2 text-sm text-gray-400 text-center">
              {formData.priority}/10
            </div>
          </div>

          {/* Account ID */}
          <div>
            <label className="block text-sm font-bold text-white mb-2">
              계정 ID (선택사항)
            </label>
            <input
              type="text"
              placeholder="계정 ID 또는 비워두기 (모든 계정)"
              value={formData.account_id || ''}
              onChange={(e) => handleChange('account_id', e.target.value || undefined)}
              className="w-full px-3 py-2 bg-slate-700 rounded border border-slate-600 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Enabled */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled !== false}
              onChange={(e) => handleChange('enabled', e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 accent-blue-500"
            />
            <label htmlFor="enabled" className="text-sm font-bold text-white">
              활성화
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-6 border-t border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-slate-700 hover:bg-slate-600 text-white transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white transition-colors font-bold"
            >
              {isSubmitting ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
