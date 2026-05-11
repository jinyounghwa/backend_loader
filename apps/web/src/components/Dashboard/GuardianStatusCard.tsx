'use client';

import { CheckCircle, AlertCircle, AlertTriangle, Server, Database, DollarSign } from 'lucide-react';

type Status = 'healthy' | 'alert' | 'warning';

interface GuardianStatusCardProps {
  title: string;
  status: Status;
  stats: {
    total?: number;
    running?: number;
    secure?: number;
    daily?: number;
    threshold?: number;
    monthly?: number;
    issues: number;
    [key: string]: number | undefined;
  };
}

export default function GuardianStatusCard({ title, status, stats }: GuardianStatusCardProps) {
  const getIcon = () => {
    switch (title) {
      case 'EC2':
        return <Server className="w-6 h-6" />;
      case 'S3':
        return <Database className="w-6 h-6" />;
      case 'Cost':
        return <DollarSign className="w-6 h-6" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'border-green-500/30 bg-green-500/5';
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-500/5';
      case 'alert':
        return 'border-red-500/30 bg-red-500/5';
      default:
        return 'border-slate-500/30 bg-slate-500/5';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'alert':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'healthy':
        return 'Healthy';
      case 'warning':
        return 'Warning';
      case 'alert':
        return 'Alert';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className={`rounded-lg border p-6 transition-all ${getStatusColor()}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-slate-400">{getIcon()}</div>
          <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-sm font-medium text-slate-300">{getStatusText()}</span>
        </div>
      </div>

      <div className="space-y-2">
        {Object.entries(stats).map(([key, value]) => {
          if (value === undefined) return null;
          return (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-slate-400 capitalize">{key}:</span>
              <span className="font-medium text-slate-200">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
