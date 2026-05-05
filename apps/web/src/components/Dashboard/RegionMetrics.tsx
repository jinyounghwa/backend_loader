'use client';

import { memo } from 'react';
import { AlertTriangle, Cpu, HardDrive, DollarSign } from 'lucide-react';
import type { EC2Data, S3Data, CostData } from '@/types/guardian';

interface RegionMetric {
  region: string;
  ec2: EC2Data;
  s3: S3Data;
  cost: CostData;
  isStale?: boolean;
}

interface RegionMetricsProps {
  metrics: RegionMetric[];
}

function RegionMetrics({ metrics }: RegionMetricsProps) {
  return (
    <div className="space-y-3">
      {metrics.map(metric => (
        <div
          key={metric.region}
          className={`bg-[#1a1d27] border border-slate-800 rounded-lg p-4 ${
            metric.isStale ? 'opacity-60' : ''
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-slate-100">{metric.region}</h3>
              {metric.isStale && (
                <span className="text-xs px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded">
                  Stale Data
                </span>
              )}
            </div>
            {metric.ec2.anomalies.length > 0 && (
              <div className="flex items-center space-x-1 text-red-400">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs font-semibold">{metric.ec2.anomalies.length} anomalies</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* EC2 Running */}
            <div className="bg-slate-700/30 rounded p-3">
              <div className="flex items-center space-x-2 mb-1">
                <Cpu className="w-4 h-4 text-green-400" />
                <span className="text-xs text-slate-400">EC2 Running</span>
              </div>
              <p className="text-lg font-bold text-slate-100">{metric.ec2.running_instances}</p>
              <p className="text-xs text-slate-500">/ {metric.ec2.total_instances} total</p>
            </div>

            {/* EC2 Stopped */}
            <div className="bg-slate-700/30 rounded p-3">
              <div className="flex items-center space-x-2 mb-1">
                <Cpu className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-400">EC2 Stopped</span>
              </div>
              <p className="text-lg font-bold text-slate-100">{metric.ec2.stopped_instances}</p>
              <p className="text-xs text-slate-500">Idle</p>
            </div>

            {/* S3 Secure */}
            <div className="bg-slate-700/30 rounded p-3">
              <div className="flex items-center space-x-2 mb-1">
                <HardDrive className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-slate-400">S3 Secure</span>
              </div>
              <p className="text-lg font-bold text-slate-100">
                {metric.s3.total_buckets - metric.s3.public_buckets.length}
              </p>
              <p className="text-xs text-slate-500">Buckets</p>
            </div>

            {/* S3 Public */}
            <div
              className={`rounded p-3 ${
                metric.s3.public_buckets.length > 0
                  ? 'bg-red-500/20'
                  : 'bg-slate-700/30'
              }`}
            >
              <div className="flex items-center space-x-2 mb-1">
                <HardDrive className={`w-4 h-4 ${
                  metric.s3.public_buckets.length > 0
                    ? 'text-red-400'
                    : 'text-slate-400'
                }`} />
                <span className="text-xs text-slate-400">S3 Public</span>
              </div>
              <p className={`text-lg font-bold ${
                metric.s3.public_buckets.length > 0
                  ? 'text-red-300'
                  : 'text-slate-100'
              }`}>
                {metric.s3.public_buckets.length}
              </p>
              <p className="text-xs text-slate-500">At risk</p>
            </div>
          </div>

          {/* Cost Info */}
          <div className="mt-3 pt-3 border-t border-slate-700 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <DollarSign className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-400">30-day cost</span>
            </div>
            <p className="text-sm font-semibold text-amber-300">
              ${metric.cost.monthly_cost.toFixed(2)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default memo(RegionMetrics);
