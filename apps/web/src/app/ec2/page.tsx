'use client';

import { useDashboard } from '@/hooks/useGuardianData';
import { mockEC2Data } from '@/lib/mock-data';
import { Server, Play, Square, AlertTriangle, ShieldAlert, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EC2Page() {
  const { summary, isLoading, isError, refresh } = useDashboard();
  const { total_instances, running_instances, stopped_instances, anomalies, exposed_instances, instances_by_region } = summary?.ec2 ?? mockEC2Data;

  const regionData = Object.entries(instances_by_region).map(([region, count]) => ({
    region,
    count,
  }));

  const riskLevel = anomalies.length > 0 ? 'HIGH' : 'LOW';
  const riskColor = riskLevel === 'HIGH' ? 'text-red-500 border-red-500/20 bg-red-500/10' : 'text-green-500 border-green-500/20 bg-green-500/10';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center">
          <Server className="w-6 h-6 mr-2 text-amber-500" />
          EC2 Instances
        </h1>
        <div className="flex items-center space-x-3 text-sm">
          <span className="text-slate-400">Exposure Risk:</span>
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

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="text-slate-400 text-sm font-medium mb-2">Total Instances</div>
          <div className="text-4xl font-bold text-slate-100 font-mono">{total_instances}</div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Running</div>
            <Play className="w-4 h-4 text-green-500" />
          </div>
          <div className="text-4xl font-bold text-green-500 font-mono">{running_instances}</div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Stopped</div>
            <Square className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-4xl font-bold text-slate-400 font-mono">{stopped_instances}</div>
        </div>

        <div className={`bg-[#1a1d27] border ${anomalies.length > 0 ? 'border-red-500/50' : 'border-slate-800'} rounded-lg p-5 relative overflow-hidden`}>
          {anomalies.length > 0 && (
            <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/10 rounded-bl-full -mr-8 -mt-8" />
          )}
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Anomalies</div>
            <AlertTriangle className={`w-4 h-4 ${anomalies.length > 0 ? 'text-red-500' : 'text-slate-500'}`} />
          </div>
          <div className={`text-4xl font-bold font-mono ${anomalies.length > 0 ? 'text-red-500' : 'text-slate-100'}`}>
            {anomalies.length}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <h2 className="text-lg font-bold text-slate-200 mb-6">Instances by Region</h2>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={regionData} margin={{ top: 5, right: 20, bottom: 25, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="region"
                  stroke="#64748b"
                  fontSize={12}
                  tickMargin={10}
                  angle={-45}
                  textAnchor="end"
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={12}
                  tickMargin={10}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{ fill: '#1e293b' }}
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                  itemStyle={{ color: '#3b82f6' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-200 flex items-center">
              <ShieldAlert className="w-5 h-5 mr-2 text-red-500" />
              Security Anomalies
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {anomalies.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500">
                No anomalies detected
              </div>
            ) : (
              anomalies.map((anomaly, idx) => (
                <div key={idx} className="bg-slate-800/30 border border-slate-700 rounded p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mr-3 ${
                        anomaly.severity === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                        anomaly.severity === 'warning' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      }`}>
                        {anomaly.severity}
                      </span>
                      <span className="text-sm font-bold text-slate-200">{anomaly.type.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <span className="text-xs font-mono text-slate-500">{anomaly.region}</span>
                  </div>
                  <div className="text-sm text-slate-300 mb-2">{anomaly.details}</div>
                  <div className="text-xs font-mono text-slate-400 bg-slate-900/50 p-2 rounded border border-slate-800">
                    ID: {anomaly.instance_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-5 border-b border-slate-800">
          <h2 className="text-lg font-bold text-slate-200">Exposed Instances</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-6 py-3 font-medium">Instance ID</th>
                <th className="px-6 py-3 font-medium">Region</th>
                <th className="px-6 py-3 font-medium">Exposed Port</th>
                <th className="px-6 py-3 font-medium">Security Group</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {exposed_instances.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                    No exposed instances found
                  </td>
                </tr>
              ) : (
                exposed_instances.map((instance, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-slate-300">{instance.instance_id}</td>
                    <td className="px-6 py-4 text-slate-400">{instance.region}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 rounded text-xs font-mono font-bold bg-red-500/10 text-red-400 border border-red-500/20">
                        {instance.port} (0.0.0.0/0)
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-400">{instance.sg_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
