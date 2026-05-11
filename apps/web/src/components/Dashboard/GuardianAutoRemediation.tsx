'use client';

import { useState } from 'react';
import { Zap, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface RemediationRule {
  id: string;
  threat_type: 'public_bucket' | 'unauthorized_region' | 'high_cost';
  enabled: boolean;
  auto_remediate: boolean;
  description: string;
  action: string;
}

interface RemediationLog {
  id: string;
  threat_id: string;
  threat_type: string;
  resource_id: string;
  action: string;
  status: 'completed' | 'pending' | 'failed';
  timestamp: string;
}

export default function GuardianAutoRemediation() {
  const [rules, setRules] = useState<RemediationRule[]>([
    {
      id: 'rule-001',
      threat_type: 'public_bucket',
      enabled: true,
      auto_remediate: true,
      description: 'Auto-block S3 public access',
      action: 'block_s3_public_access',
    },
    {
      id: 'rule-002',
      threat_type: 'unauthorized_region',
      enabled: true,
      auto_remediate: true,
      description: 'Auto-stop EC2 in unauthorized regions',
      action: 'stop_ec2_instance',
    },
    {
      id: 'rule-003',
      threat_type: 'high_cost',
      enabled: true,
      auto_remediate: false,
      description: 'Alert admin on high cost spike',
      action: 'alert_admin',
    },
  ]);

  const [logs, setLogs] = useState<RemediationLog[]>([
    {
      id: 'log-001',
      threat_id: 'threat-001',
      threat_type: 'public_bucket',
      resource_id: 'my-bucket-name',
      action: 'block_s3_public_access',
      status: 'completed',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'log-002',
      threat_id: 'threat-002',
      threat_type: 'unauthorized_region',
      resource_id: 'i-1234567890abcdef0',
      action: 'stop_ec2_instance',
      status: 'completed',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
    },
  ]);

  const handleToggleRule = (ruleId: string) => {
    setRules((prev) =>
      prev.map((rule) =>
        rule.id === ruleId
          ? { ...rule, auto_remediate: !rule.auto_remediate }
          : rule
      )
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'pending':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);

    if (diffInMinutes < 1) return '방금';
    if (diffInMinutes < 60) return `${diffInMinutes}분 전`;
    return `${diffInHours}시간 전`;
  };

  return (
    <div className="space-y-6">
      {/* Remediation Rules */}
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
        <div className="mb-4 flex items-center gap-3">
          <Shield className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-semibold text-slate-100">Auto-Remediation Rules</h2>
        </div>

        <div className="space-y-3">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center justify-between rounded border border-slate-700/30 bg-slate-800/30 px-4 py-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  <span className="font-semibold text-slate-100">{rule.description}</span>
                </div>
                <div className="text-xs text-slate-400">
                  Type: {rule.threat_type} | Action: {rule.action}
                </div>
              </div>
              <label className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-300">
                  {rule.auto_remediate ? 'Auto' : 'Manual'}
                </span>
                <input
                  type="checkbox"
                  checked={rule.auto_remediate}
                  onChange={() => handleToggleRule(rule.id)}
                  className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
                />
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Remediation Log */}
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold text-slate-100">Remediation History</h2>

        <div className="space-y-2">
          {logs.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-slate-400">No remediation actions yet</div>
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="flex items-start gap-4 rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3"
              >
                <div className="mt-1">{getStatusIcon(log.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-slate-100">{log.action}</span>
                    <span className="text-xs text-slate-500">{getRelativeTime(log.timestamp)}</span>
                  </div>
                  <div className="text-xs text-slate-400">
                    Type: {log.threat_type} | Resource: {log.resource_id}
                  </div>
                  <div className="mt-2">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                        log.status === 'completed'
                          ? 'bg-green-500/10 text-green-400'
                          : log.status === 'pending'
                            ? 'bg-yellow-500/10 text-yellow-400'
                            : 'bg-red-500/10 text-red-400'
                      }`}
                    >
                      {log.status}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
