'use client';

import { useState, useEffect, useCallback, memo } from 'react';
import { Plus, Trash2, Play, CheckCircle, AlertCircle } from 'lucide-react';
import useSWR from 'swr';

interface ResponseRule {
  rule_id: string;
  region: string;
  event_type: string;
  action: string;
  enabled: boolean;
  priority: number;
  dry_run: boolean;
  created_at: string;
  created_by?: string;
}

interface RuleManagerProps {
  region?: string;
  onRuleCreate?: (rule: ResponseRule) => void;
}

const fetcher = (url: string) => fetch(url).then(res => res.json());

function ResponseRuleManager({ region, onRuleCreate }: RuleManagerProps) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<Partial<ResponseRule>>({
    event_type: 'unauthorized_region',
    action: 'stop_instance',
    enabled: true,
    priority: 100,
    dry_run: false,
  });

  const url = `/api/response-rules${region ? `?region=${region}` : ''}`;
  const { data, isLoading, error, mutate } = useSWR<{ rules: ResponseRule[] }>(url, fetcher, {
    refreshInterval: 60000,
  });

  const rules = data?.rules ?? [];

  const handleCreateRule = useCallback(async () => {
    if (!formData.rule_id || !formData.region || !formData.event_type || !formData.action) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      const response = await fetch('/api/response-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const { rule } = await response.json();
        setFormData({
          event_type: 'unauthorized_region',
          action: 'stop_instance',
          enabled: true,
          priority: 100,
          dry_run: false,
        });
        setShowForm(false);
        mutate();
        onRuleCreate?.(rule);
      }
    } catch (err) {
      alert('Failed to create rule');
    }
  }, [formData, mutate, onRuleCreate]);

  const handleDeleteRule = useCallback(
    async (ruleId: string) => {
      if (!confirm('Delete this rule?')) return;

      try {
        const response = await fetch(`/api/response-rules?rule_id=${ruleId}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          mutate();
        }
      } catch (err) {
        alert('Failed to delete rule');
      }
    },
    [mutate]
  );

  const eventTypeLabel = (et: string) => et.replace('_', ' ').toUpperCase();
  const actionLabel = (a: string) => a.replace('_', ' ').toUpperCase();

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-200">Response Rules</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center space-x-2 px-3 py-2 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span className="text-xs font-medium">New Rule</span>
        </button>
      </div>

      {showForm && (
        <div className="p-4 bg-slate-800/30 border-b border-slate-800 space-y-3">
          <input
            type="text"
            placeholder="Rule ID (e.g., rule-001)"
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm text-slate-100 placeholder-slate-500"
            value={formData.rule_id ?? ''}
            onChange={e => setFormData({ ...formData, rule_id: e.target.value })}
          />
          <select
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm text-slate-100"
            value={formData.region ?? 'ap-northeast-1'}
            onChange={e => setFormData({ ...formData, region: e.target.value })}
          >
            <option value="ap-northeast-1">Tokyo (ap-northeast-1)</option>
            <option value="us-east-1">N. Virginia (us-east-1)</option>
            <option value="eu-west-1">Ireland (eu-west-1)</option>
            <option value="*">Global (*)</option>
          </select>
          <select
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm text-slate-100"
            value={formData.event_type ?? 'unauthorized_region'}
            onChange={e => setFormData({ ...formData, event_type: e.target.value })}
          >
            <option value="unauthorized_region">Unauthorized Region</option>
            <option value="open_port">Open Port</option>
            <option value="public_bucket">Public Bucket</option>
            <option value="new_instance">New Instance</option>
          </select>
          <select
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm text-slate-100"
            value={formData.action ?? 'stop_instance'}
            onChange={e => setFormData({ ...formData, action: e.target.value })}
          >
            <option value="stop_instance">Stop Instance</option>
            <option value="block_bucket">Block Bucket</option>
            <option value="revoke_key">Revoke Key</option>
          </select>

          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 text-sm text-slate-400">
              <input
                type="checkbox"
                checked={formData.enabled ?? true}
                onChange={e => setFormData({ ...formData, enabled: e.target.checked })}
                className="rounded"
              />
              <span>Enabled</span>
            </label>
            <label className="flex items-center space-x-2 text-sm text-slate-400">
              <input
                type="checkbox"
                checked={formData.dry_run ?? false}
                onChange={e => setFormData({ ...formData, dry_run: e.target.checked })}
                className="rounded"
              />
              <span>Dry Run (Test Only)</span>
            </label>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm text-slate-400">Priority:</label>
            <input
              type="number"
              min="1"
              max="1000"
              className="w-20 px-2 py-1 bg-slate-900 border border-slate-700 rounded text-sm text-slate-100"
              value={formData.priority ?? 100}
              onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) })}
            />
            <span className="text-xs text-slate-500">(Lower = Higher)</span>
          </div>

          <div className="flex items-center space-x-2 pt-2">
            <button
              onClick={handleCreateRule}
              className="flex-1 px-3 py-2 bg-green-500/20 text-green-400 rounded text-sm font-medium hover:bg-green-500/30 transition-colors"
            >
              Create Rule
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="flex-1 px-3 py-2 bg-slate-700/20 text-slate-400 rounded text-sm font-medium hover:bg-slate-700/30 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
            <tr>
              <th className="px-6 py-3 font-medium">Rule ID</th>
              <th className="px-6 py-3 font-medium">Region</th>
              <th className="px-6 py-3 font-medium">Event Type</th>
              <th className="px-6 py-3 font-medium">Action</th>
              <th className="px-6 py-3 font-medium hidden sm:table-cell">Priority</th>
              <th className="px-6 py-3 font-medium hidden md:table-cell">Mode</th>
              <th className="px-6 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {rules.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                  {isLoading ? 'Loading...' : 'No rules found'}
                </td>
              </tr>
            ) : (
              rules.map(rule => (
                <tr key={rule.rule_id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="px-6 py-3 font-mono text-slate-300 text-xs">{rule.rule_id}</td>
                  <td className="px-6 py-3 text-slate-400 text-xs">
                    <span className="px-2 py-1 rounded bg-slate-700/30 font-mono">
                      {rule.region}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-slate-300 text-xs">
                    {eventTypeLabel(rule.event_type)}
                  </td>
                  <td className="px-6 py-3 text-slate-300 text-xs">
                    {actionLabel(rule.action)}
                  </td>
                  <td className="px-6 py-3 text-slate-400 text-xs hidden sm:table-cell">
                    {rule.priority}
                  </td>
                  <td className="px-6 py-3 hidden md:table-cell">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        rule.dry_run
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : rule.enabled
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-slate-700/30 text-slate-400'
                      }`}
                    >
                      {rule.dry_run ? 'DRY RUN' : rule.enabled ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </td>
                  <td className="px-6 py-3 flex items-center space-x-2">
                    <button
                      onClick={() => alert('Dry-run test feature coming soon')}
                      className="p-1 text-slate-400 hover:text-blue-400 transition-colors"
                      title="Test rule"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteRule(rule.rule_id)}
                      className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete rule"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default memo(ResponseRuleManager);
