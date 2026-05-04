'use client';

import { memo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { CostData, EC2Data, S3Data } from '@/types/guardian';

interface ChartSectionProps {
  cost: CostData;
  ec2: EC2Data;
  s3: S3Data;
}

function ChartSection({ cost, ec2, s3 }: ChartSectionProps) {
  const resourceData = [
    { name: 'EC2 Running', value: ec2.running_instances, color: '#22c55e' },
    { name: 'EC2 Stopped', value: ec2.stopped_instances, color: '#64748b' },
    { name: 'S3 Secure', value: s3.total_buckets - s3.public_buckets.length, color: '#3b82f6' },
    { name: 'S3 Public', value: s3.public_buckets.length, color: '#ef4444' },
  ];

  return (
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
  );
}

export default memo(ChartSection);
