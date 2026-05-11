'use client';

import { useState } from 'react';
import { Bell, Check, X, AlertCircle } from 'lucide-react';

interface NotificationConfig {
  slack_enabled: boolean;
  slack_webhook?: string;
  pagerduty_enabled: boolean;
  pagerduty_routing_key?: string;
  telegram_enabled: boolean;
  email_enabled: boolean;
  notification_levels: {
    high: boolean;
    medium: boolean;
    info: boolean;
  };
}

export default function GuardianNotificationSettings() {
  const [config, setConfig] = useState<NotificationConfig>({
    slack_enabled: !!process.env.NEXT_PUBLIC_SLACK_CONFIGURED,
    pagerduty_enabled: !!process.env.NEXT_PUBLIC_PAGERDUTY_CONFIGURED,
    telegram_enabled: true,
    email_enabled: false,
    notification_levels: {
      high: true,
      medium: true,
      info: false,
    },
  });

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleToggle = (key: keyof NotificationConfig) => {
    if (typeof config[key] === 'boolean') {
      setConfig((prev) => ({
        ...prev,
        [key]: !prev[key],
      }));
    }
  };

  const handleLevelToggle = (level: keyof NotificationConfig['notification_levels']) => {
    setConfig((prev) => ({
      ...prev,
      notification_levels: {
        ...prev.notification_levels,
        [level]: !prev.notification_levels[level],
      },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // 실제로는 서버에 저장해야 하지만, 여기서는 로컬에만 저장
      localStorage.setItem('guardianNotificationConfig', JSON.stringify(config));
      setMessage({ type: 'success', text: 'Notification settings saved' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings' });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
      <div className="mb-6 flex items-center gap-3">
        <Bell className="w-5 h-5 text-slate-400" />
        <h2 className="text-lg font-semibold text-slate-100">Notification Settings</h2>
      </div>

      {message && (
        <div
          className={`mb-4 flex items-center gap-2 rounded px-4 py-3 text-sm ${
            message.type === 'success'
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          }`}
        >
          {message.type === 'success' ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      {/* Notification Channels */}
      <div className="mb-6 space-y-3">
        <h3 className="text-sm font-semibold text-slate-200">Notification Channels</h3>

        {/* Slack */}
        <div className="flex items-center justify-between rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.slack_enabled}
              onChange={() => handleToggle('slack_enabled')}
              className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <div className="font-medium text-slate-100">Slack</div>
              <div className="text-xs text-slate-400">
                {config.slack_enabled ? 'Configured' : 'Not configured'}
              </div>
            </div>
          </div>
          {config.slack_enabled && <Check className="w-4 h-4 text-green-500" />}
        </div>

        {/* PagerDuty */}
        <div className="flex items-center justify-between rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.pagerduty_enabled}
              onChange={() => handleToggle('pagerduty_enabled')}
              className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <div className="font-medium text-slate-100">PagerDuty</div>
              <div className="text-xs text-slate-400">
                {config.pagerduty_enabled ? 'Configured' : 'Not configured'}
              </div>
            </div>
          </div>
          {config.pagerduty_enabled && <Check className="w-4 h-4 text-green-500" />}
        </div>

        {/* Telegram */}
        <div className="flex items-center justify-between rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.telegram_enabled}
              onChange={() => handleToggle('telegram_enabled')}
              className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <div className="font-medium text-slate-100">Telegram</div>
              <div className="text-xs text-slate-400">Configured</div>
            </div>
          </div>
          {config.telegram_enabled && <Check className="w-4 h-4 text-green-500" />}
        </div>
      </div>

      {/* Alert Levels */}
      <div className="mb-6 space-y-3">
        <h3 className="text-sm font-semibold text-slate-200">Alert Levels</h3>
        <div className="space-y-2">
          {[
            { level: 'high' as const, label: 'High Severity', color: 'bg-red-500/10' },
            { level: 'medium' as const, label: 'Medium Severity', color: 'bg-yellow-500/10' },
            { level: 'info' as const, label: 'Info Only', color: 'bg-blue-500/10' },
          ].map(({ level, label, color }) => (
            <div key={level} className={`flex items-center justify-between rounded px-4 py-3 ${color}`}>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.notification_levels[level]}
                  onChange={() => handleLevelToggle(level)}
                  className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-slate-200">{label}</span>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Info */}
      <div className="mb-6 flex items-start gap-3 rounded border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
        <AlertCircle className="mt-0.5 w-4 h-4 text-yellow-500 flex-shrink-0" />
        <div className="text-sm text-yellow-600">
          For Slack and PagerDuty integration, configure environment variables:
          <div className="mt-2 space-y-1 font-mono text-xs">
            <div>SLACK_WEBHOOK_URL</div>
            <div>PAGERDUTY_ROUTING_KEY</div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-all hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
