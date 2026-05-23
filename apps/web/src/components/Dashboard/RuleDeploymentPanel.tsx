'use client';

import { useState, useEffect } from 'react';
import { Upload, AlertCircle, CheckCircle, Clock, Trash2 } from 'lucide-react';
import { SecurityRule } from '@/lib/hooks/useSecurityRules';

interface Deployment {
  deployment_id: string;
  rule_id: string;
  status: 'PENDING' | 'ACTIVE' | 'FAILED' | 'ROLLED_BACK';
  deployment_date: string;
  deployed_by?: string;
  error_message?: string;
}

interface RuleDeploymentPanelProps {
  rule: SecurityRule;
  onDeploymentSuccess?: (deployment: Deployment) => void;
}

export function RuleDeploymentPanel({ rule, onDeploymentSuccess }: RuleDeploymentPanelProps) {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDeployment, setSelectedDeployment] = useState<string | null>(null);

  // Load deployment history
  useEffect(() => {
    loadDeploymentHistory();
  }, [rule.rule_id]);

  const loadDeploymentHistory = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/guardian/rules/${rule.rule_id}/deployments`
      );

      if (response.ok) {
        const data = await response.json();
        setDeployments(data.deployments || []);
      } else {
        console.warn('Failed to load deployment history');
        setDeployments([]);
      }
    } catch (err) {
      console.error('Error loading deployment history:', err);
      setDeployments([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/guardian/rules/${rule.rule_id}/deploy`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            status: 'ACTIVE',
            deployed_by: 'user',
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error_message || 'Deployment failed');
      }

      const data = await response.json();

      // Add new deployment to list
      const newDeployment: Deployment = {
        deployment_id: data.deployment_id,
        rule_id: rule.rule_id,
        status: 'ACTIVE',
        deployment_date: data.deployment_date,
        deployed_by: 'user',
      };

      setDeployments([newDeployment, ...deployments]);
      onDeploymentSuccess?.(newDeployment);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsDeploying(false);
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'PENDING':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'FAILED':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'ROLLED_BACK':
        return 'bg-gray-500/10 text-gray-400 border-gray-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return <CheckCircle className="w-4 h-4" />;
      case 'PENDING':
        return <Clock className="w-4 h-4" />;
      case 'FAILED':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const activeCount = deployments.filter(d => d.status === 'ACTIVE').length;
  const totalCount = deployments.length;

  return (
    <div className="space-y-4">
      {/* Deployment Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">활성 배포</div>
          <div className="text-2xl font-bold text-white">{activeCount}</div>
        </div>
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="text-sm text-gray-400 mb-1">전체 배포</div>
          <div className="text-2xl font-bold text-white">{totalCount}</div>
        </div>
      </div>

      {/* Deploy Button */}
      <div className="flex gap-2">
        <button
          onClick={handleDeploy}
          disabled={isDeploying || rule.enabled === false}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
        >
          <Upload className="w-4 h-4" />
          {isDeploying ? '배포 중...' : '규칙 배포'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Deployment History */}
      <div className="space-y-3">
        <h3 className="text-lg font-bold text-white">배포 이력</h3>

        {isLoading ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            로드 중...
          </div>
        ) : deployments.length === 0 ? (
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center text-gray-400">
            배포 이력이 없습니다
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">배포 ID</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">상태</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">배포 시간</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-semibold">배포자</th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((deployment, index) => (
                  <tr
                    key={deployment.deployment_id}
                    className={`border-b border-slate-700 ${
                      selectedDeployment === deployment.deployment_id
                        ? 'bg-slate-700/50'
                        : 'hover:bg-slate-800/50'
                    } cursor-pointer transition-colors`}
                    onClick={() => setSelectedDeployment(deployment.deployment_id)}
                  >
                    <td className="px-4 py-3 text-white font-mono text-xs">
                      {deployment.deployment_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-2 px-3 py-1 rounded border ${getStatusColor(
                          deployment.status
                        )}`}
                      >
                        {getStatusIcon(deployment.status)}
                        {deployment.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {new Date(deployment.deployment_date).toLocaleString('ko-KR')}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {deployment.deployed_by || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Error Message Display */}
      {selectedDeployment && deployments.find(d => d.deployment_id === selectedDeployment)?.error_message && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="text-sm font-semibold text-red-400 mb-1">배포 오류</div>
          <div className="text-xs text-red-400">
            {deployments.find(d => d.deployment_id === selectedDeployment)?.error_message}
          </div>
        </div>
      )}
    </div>
  );
}
