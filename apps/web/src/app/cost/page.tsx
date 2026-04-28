'use client';

import { useDashboard } from '@/hooks/useGuardianData';
import { mockCostData } from '@/lib/mock-data';
import { DollarSign, TrendingUp, TrendingDown, AlertTriangle, Calendar, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function CostPage() {
  const { summary, isLoading, isError, refresh } = useDashboard();
  const cost = summary?.cost ?? mockCostData;
  const { today_cost, yesterday_cost, monthly_cost, increase_percent, threshold, is_anomaly, daily_costs } = cost;

  const trend = increase_percent > 0 ? 'up' : 'down';
  const trendColor = is_anomaly ? 'text-red-500' : trend === 'up' ? 'text-amber-500' : 'text-green-500';
  const TrendIcon = trend === 'up' ? TrendingUp : TrendingDown;

  const projectedMonthly = (monthly_cost / new Date().getDate()) * 30;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center">
          <DollarSign className="w-6 h-6 mr-2 text-amber-500" />
          Cost Analysis
        </h1>
        <div className="flex items-center space-x-3 text-sm">
          <span className="text-slate-400">Daily Threshold:</span>
          <span className="px-2 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700 font-mono font-medium">
            ${threshold.toFixed(2)}
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
        <div className={`bg-[#1a1d27] border ${is_anomaly ? 'border-red-500/50' : 'border-slate-800'} rounded-lg p-5 relative overflow-hidden`}>
          {is_anomaly && (
            <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/10 rounded-bl-full -mr-8 -mt-8" />
          )}
          <div className="text-slate-400 text-sm font-medium mb-2">Today&apos;s Cost</div>
          <div className="flex items-end justify-between">
            <div className={`text-4xl font-bold font-mono ${is_anomaly ? 'text-red-500' : 'text-slate-100'}`}>
              ${today_cost.toFixed(2)}
            </div>
            <div className={`flex items-center text-sm font-mono ${trendColor} mb-1`}>
              <TrendIcon className="w-4 h-4 mr-1" />
              {Math.abs(increase_percent)}%
            </div>
          </div>
          {is_anomaly && (
            <div className="mt-3 flex items-center text-xs text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
              <AlertTriangle className="w-3 h-3 mr-1.5" />
              Exceeds daily threshold
            </div>
          )}
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="text-slate-400 text-sm font-medium mb-2">Yesterday&apos;s Cost</div>
          <div className="text-4xl font-bold text-slate-300 font-mono">
            ${yesterday_cost.toFixed(2)}
          </div>
        </div>

        <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between items-start mb-2">
            <div className="text-slate-400 text-sm font-medium">Monthly Projection</div>
            <Calendar className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-4xl font-bold text-slate-100 font-mono">
            ${projectedMonthly.toFixed(2)}
          </div>
          <div className="mt-2 text-xs text-slate-500 font-mono">
            Current: ${monthly_cost.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
        <h2 className="text-lg font-bold text-slate-200 mb-6">30-Day Cost Trend</h2>
        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={daily_costs} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
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
              <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Threshold', fill: '#ef4444', fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 3, fill: '#1e293b', stroke: '#f59e0b', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#f59e0b', stroke: '#1e293b', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-5 border-b border-slate-800">
          <h2 className="text-lg font-bold text-slate-200">Recent Daily Costs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-400 uppercase bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-6 py-3 font-medium">Date</th>
                <th className="px-6 py-3 font-medium">Cost</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {[...daily_costs].reverse().slice(0, 7).map((day) => {
                const isOver = day.cost > threshold;
                return (
                  <tr key={day.date} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-slate-300">{day.date}</td>
                    <td className="px-6 py-4 font-mono font-bold text-slate-200">${day.cost.toFixed(2)}</td>
                    <td className="px-6 py-4">
                      {isOver ? (
                        <span className="px-2.5 py-1 rounded text-xs font-medium border bg-red-500/10 text-red-400 border-red-500/20">
                          EXCEEDED
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded text-xs font-medium border bg-green-500/10 text-green-400 border-green-500/20">
                          NORMAL
                        </span>
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
