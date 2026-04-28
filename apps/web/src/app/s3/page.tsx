'use client';

import { useDashboard } from '@/hooks/useGuardianData';
import { mockS3Data } from '@/lib/mock-data';
import { Database, Globe, PlusCircle, Shield, ShieldAlert, RefreshCw } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

export default function S3Page() {
  const { summary, isLoading, isError, refresh } = useDashboard();
  const { total_buckets, public_buckets, new_buckets, anomalies } = summary?.s3 ?? mockS3Data;

  const secureBuckets = total_buckets - public_buckets.length;
  const securityData = [
    { name: 'Secure', value: secureBuckets, color: '#22c55e' },
    { name: 'Public/At-Risk', value: public_buckets.length, color: '#ef4444' },
  ];

  const riskLevel = public_buckets.length > 0 ? 'CRITICAL' : 'LOW';
  const riskColor = riskLevel === 'CRITICAL' ? 'text-red-500 border-red-500/20 bg-red-500/10' : 'text-green-500 border-green-500/20 bg-green-500/10';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center">
          <Database className="w-6 h-6 mr-2 text-amber-500" />
          S3 Buckets
        </h1>
        <div className="flex items-center space-x-3 text-sm">
          <span className="text-slate-400">Security Status:</span>
          <span className={`px-2 py-1 rounded border font-mono font-medium ${riskColor}`}>
            {riskLevel}
          </span>
          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          {isError && <span className="text-xs text-red-400">Fallback data</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Total Buckets</div>
            <Database className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-4xl font-bold text-slate-100 font-mono">{total_buckets}</div>
        </div>

        <div className={`bg-[#1a1d27] border ${public_buckets.length > 0 ? 'border-red-500/50' : 'border-slate-800'} rounded-lg p-5 relative overflow-hidden`}>
          {public_buckets.length > 0 && (
            <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/10 rounded-bl-full -mr-8 -mt-8" />
          )}
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Public Buckets</div>
            <Globe className={`w-4 h-4 ${public_buckets.length > 0 ? 'text-red-500' : 'text-slate-500'}`} />
          </div>
          <div className={`text-4xl font-bold font-mono ${public_buckets.length > 0 ? 'text-red-500' : 'text-slate-100'}`}>
            {public_buckets.length}
          </div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">New (24h)</div>
            <PlusCircle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-4xl font-bold text-amber-500 font-mono">{new_buckets.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <h2 className="text-lg font-bold text-slate-200 mb-6">Security Status</h2>
          <div className="h-64 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={securityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {securityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc', borderRadius: '0.375rem' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center flex-col pointer-events-none">
              {public_buckets.length === 0 ? (
                <Shield className="w-10 h-10 text-green-500 mb-1" />
              ) : (
                <ShieldAlert className="w-10 h-10 text-red-500 mb-1" />
              )}
              <span className={`text-sm font-bold ${public_buckets.length === 0 ? 'text-green-500' : 'text-red-500'}`}>
                {public_buckets.length === 0 ? 'SECURE' : 'AT RISK'}
              </span>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {securityData.map((item) => (
              <div key={item.name} className="flex items-center text-xs">
                <div className="w-3 h-3 rounded-sm mr-2" style={{ backgroundColor: item.color }} />
                <span className="text-slate-400 truncate">{item.name} ({item.value})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-200 flex items-center">
                <Globe className="w-5 h-5 mr-2 text-red-500" />
                Public Buckets
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3 font-medium">Bucket Name</th>
                    <th className="px-6 py-3 font-medium">Exposure Reason</th>
                    <th className="px-6 py-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {public_buckets.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-6 py-8 text-center text-slate-500">
                        No public buckets found
                      </td>
                    </tr>
                  ) : (
                    public_buckets.map((bucket, idx) => {
                      const date = new Date(bucket.created);
                      return (
                        <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-6 py-4 font-mono text-slate-300">{bucket.bucket_name}</td>
                          <td className="px-6 py-4">
                            <div className="flex flex-col space-y-1">
                              {bucket.public_reasons.map((reason, i) => (
                                <span key={i} className="px-2 py-1 rounded text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 inline-block w-fit">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                            {date.toLocaleDateString()} {date.toLocaleTimeString()}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-200 flex items-center">
                <PlusCircle className="w-5 h-5 mr-2 text-amber-500" />
                New Buckets (Last 24h)
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3 font-medium">Bucket Name</th>
                    <th className="px-6 py-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {new_buckets.length === 0 ? (
                    <tr>
                      <td colSpan={2} className="px-6 py-8 text-center text-slate-500">
                        No new buckets found
                      </td>
                    </tr>
                  ) : (
                    new_buckets.map((bucket, idx) => {
                      const date = new Date(bucket.created);
                      return (
                        <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-6 py-4 font-mono text-slate-300">{bucket.bucket_name}</td>
                          <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                            {date.toLocaleDateString()} {date.toLocaleTimeString()}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
