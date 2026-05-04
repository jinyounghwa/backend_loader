'use client';

import { useDashboard } from '@/hooks/useGuardianData';
import { mockDashboardSummary } from '@/lib/mock-data';
import { DollarSign, Server, Database, AlertTriangle, ArrowUpRight, ArrowDownRight, Activity, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import AccountSelector from '@/components/Dashboard/AccountSelector';
import RiskScore from '@/components/Dashboard/RiskScore';
import EventFeed from '@/components/Dashboard/EventFeed';
import ActionHistory from '@/components/Dashboard/ActionHistory';
import AuditLogViewer from '@/components/Dashboard/AuditLogViewer';

export default function DashboardPage() {
  const { summary, isLoading, isError, refresh } = useDashboard();
  const data = summary ?? mockDashboardSummary;
  const { cost, ec2, s3, recent_events, system_health } = data;

  const costTrend = cost.increase_percent > 0 ? 'up' : 'down';
  const costTrendColor = cost.is_anomaly ? 'text-red-500' : costTrend === 'up' ? 'text-amber-500' : 'text-green-500';

  const resourceData = [
    { name: 'EC2 Running', value: ec2.running_instances, color: '#22c55e' },
    { name: 'EC2 Stopped', value: ec2.stopped_instances, color: '#64748b' },
    { name: 'S3 Secure', value: s3.total_buckets - s3.public_buckets.length, color: '#3b82f6' },
    { name: 'S3 Public', value: s3.public_buckets.length, color: '#ef4444' },
  ];

  const healthLabel = system_health.toUpperCase();
  const healthClass = system_health === 'critical'
    ? 'bg-red-500/10 text-red-500 border-red-500/20'
    : system_health === 'warning'
      ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
      : 'bg-green-500/10 text-green-500 border-green-500/20';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3 md:gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-100 tracking-tight">System Overview</h1>
          <div className="mt-2">
            <AccountSelector />
          </div>
        </div>
        <div className="flex items-center space-x-2 md:space-x-3 text-xs md:text-sm">
          <span className="text-slate-400">Status:</span>
          <span className={`px-2 py-1 rounded border font-mono font-medium ${healthClass}`}>
            {healthLabel}
          </span>
          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-3 md:p-5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-3 md:mb-4">
            <div className="p-1.5 md:p-2 bg-slate-800/50 rounded-md border border-slate-700/50">
              <DollarSign className="w-4 md:w-5 h-4 md:h-5 text-slate-300" />
            </div>
            <div className={`flex items-center text-xs md:text-sm font-mono ${costTrendColor}`}>
              {costTrend === 'up' ? <ArrowUpRight className="w-3 md:w-4 h-3 md:h-4 mr-1" /> : <ArrowDownRight className="w-3 md:w-4 h-3 md:h-4 mr-1" />}
              {Math.abs(cost.increase_percent)}%
            </div>
          </div>
          <div className="text-slate-400 text-xs md:text-sm font-medium mb-1">Today&apos;s Cost</div>
          <div className="text-2xl md:text-3xl font-bold text-slate-100 font-mono">${cost.today_cost.toFixed(2)}</div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-3 md:p-5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-green-500/5 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-3 md:mb-4">
            <div className="p-1.5 md:p-2 bg-slate-800/50 rounded-md border border-slate-700/50">
              <Server className="w-4 md:w-5 h-4 md:h-5 text-slate-300" />
            </div>
            <div className="flex items-center text-xs md:text-sm font-mono text-slate-400">
              {ec2.total_instances} Total
            </div>
          </div>
          <div className="text-slate-400 text-xs md:text-sm font-medium mb-1">Running EC2</div>
          <div className="text-2xl md:text-3xl font-bold text-slate-100 font-mono">{ec2.running_instances}</div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-3 md:p-5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/5 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-3 md:mb-4">
            <div className="p-1.5 md:p-2 bg-slate-800/50 rounded-md border border-slate-700/50">
              <Database className="w-4 md:w-5 h-4 md:h-5 text-slate-300" />
            </div>
            <div className="flex items-center text-xs md:text-sm font-mono text-amber-500">
              {s3.new_buckets.length} New
            </div>
          </div>
          <div className="text-slate-400 text-xs md:text-sm font-medium mb-1">Total S3 Buckets</div>
          <div className="text-2xl md:text-3xl font-bold text-slate-100 font-mono">{s3.total_buckets}</div>
        </div>

        <div className="bg-[#1a1d27] border border-red-900/30 rounded-lg p-3 md:p-5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/5 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-3 md:mb-4">
            <div className="p-1.5 md:p-2 bg-red-500/10 rounded-md border border-red-500/20">
              <AlertTriangle className="w-4 md:w-5 h-4 md:h-5 text-red-500" />
            </div>
            <div className="flex items-center text-xs md:text-sm font-mono text-red-500 animate-pulse">
              Action Req.
            </div>
          </div>
          <div className="text-slate-400 text-xs md:text-sm font-medium mb-1">Active Alerts</div>
          <div className="text-2xl md:text-3xl font-bold text-red-500 font-mono">{ec2.anomalies.length + s3.anomalies.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <div className="lg:col-span-2 bg-[#1a1d27] border border-slate-800 rounded-lg p-3 md:p-5">
          <div className="flex items-center justify-between mb-4 md:mb-6 flex-col md:flex-row gap-2">
            <h2 className="text-base md:text-lg font-bold text-slate-200">Cost Trend (30 Days)</h2>
            <div className="text-xs md:text-sm text-slate-400 font-mono">Threshold: ${cost.threshold}/day</div>
          </div>
          <div className="h-48 md:h-64 lg:h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cost.daily_costs} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#64748b"
                  fontSize={12}
                  tickFormatter={(val) => val.split('-').slice(1).join('/')}
                  tickMargin={10}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={12}
                  tickFormatter={(val) => `$${val}`}
                  tickMargin={10}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                  itemStyle={{ color: '#f59e0b' }}
                  formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Cost']}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="cost"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: '#f59e0b', stroke: '#1e293b', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-3 md:p-5">
          <h2 className="text-base md:text-lg font-bold text-slate-200 mb-4 md:mb-6">Resource Distribution</h2>
          <div className="h-48 md:h-56 lg:h-64 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={resourceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {resourceData.map((entry, index) => (
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
              <span className="text-xl md:text-2xl font-bold text-slate-200 font-mono">{ec2.total_instances + s3.total_buckets}</span>
              <span className="text-xs text-slate-500 uppercase tracking-wider">Total</span>
            </div>
          </div>
          <div className="mt-3 md:mt-4 grid grid-cols-2 gap-2">
            {resourceData.map((item) => (
              <div key={item.name} className="flex items-center text-xs">
                <div className="w-2 h-2 md:w-3 md:h-3 rounded-sm mr-2" style={{ backgroundColor: item.color }} />
                <span className="text-slate-400 truncate text-xs md:text-sm">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <div>
          <RiskScore
            criticalCount={ec2.anomalies.length}
            highCount={s3.anomalies.length}
            mediumCount={ec2.anomalies.length > 0 ? Math.ceil(ec2.anomalies.length / 2) : 0}
            totalIssues={ec2.anomalies.length + s3.anomalies.length + (ec2.anomalies.length > 0 ? Math.ceil(ec2.anomalies.length / 2) : 0)}
          />
        </div>
        <div className="lg:col-span-2">
          <EventFeed />
        </div>
      </div>

      <ActionHistory />

      <AuditLogViewer limit={50} />

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-3 md:p-5 border-b border-slate-800 flex items-center justify-between flex-col md:flex-row gap-2">
          <h2 className="text-base md:text-lg font-bold text-slate-200 flex items-center">
            <Activity className="w-4 md:w-5 h-4 md:h-5 mr-2 text-slate-400" />
            Event Log
          </h2>
          {isError && <span className="text-xs text-red-400">API unavailable — showing fallback data</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs md:text-sm text-left">
            <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-2 md:px-6 py-2 md:py-3 font-medium">Time</th>
                <th className="px-2 md:px-6 py-2 md:py-3 font-medium hidden sm:table-cell">Type</th>
                <th className="px-2 md:px-6 py-2 md:py-3 font-medium hidden md:table-cell">Severity</th>
                <th className="px-2 md:px-6 py-2 md:py-3 font-medium hidden lg:table-cell">Message</th>
                <th className="px-2 md:px-6 py-2 md:py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {recent_events.map((event, idx) => {
                const date = new Date(event.timestamp);
                const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                let severityClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                if (event.severity === 'critical') severityClass = 'bg-red-500/10 text-red-400 border-red-500/20';
                if (event.severity === 'warning') severityClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';

                return (
                  <tr key={event.event_id ?? idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-2 md:px-6 py-2 md:py-4 font-mono text-slate-400 whitespace-nowrap text-xs md:text-sm">{timeStr}</td>
                    <td className="px-2 md:px-6 py-2 md:py-4 hidden sm:table-cell">
                      <span className="uppercase tracking-wider text-xs font-bold text-slate-300">
                        {event.event_type.replace('_', ' ').substring(0, 10)}
                      </span>
                    </td>
                    <td className="px-2 md:px-6 py-2 md:py-4 hidden md:table-cell">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${severityClass}`}>
                        {event.severity.substring(0, 3).toUpperCase()}
                      </span>
                    </td>
                    <td className="px-2 md:px-6 py-2 md:py-4 text-slate-300 hidden lg:table-cell">{(event.details?.message ?? '-').substring(0, 30)}</td>
                    <td className="px-2 md:px-6 py-2 md:py-4">
                      {event.auto_response ? (
                        <span className={`flex items-center text-xs font-medium ${
                          event.auto_response.status === 'success' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          <div className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                            event.auto_response.status === 'success' ? 'bg-green-400' : 'bg-red-400'
                          }`} />
                          {event.auto_response.action}
                        </span>
                      ) : (
                        <span className="text-slate-500 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
