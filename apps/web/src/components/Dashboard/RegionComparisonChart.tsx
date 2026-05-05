'use client';

import { memo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface RegionCost {
  region: string;
  cost: number;
  displayName: string;
}

interface RegionComparisonChartProps {
  data: RegionCost[];
}

function RegionComparisonChart({ data }: RegionComparisonChartProps) {
  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <div className="mb-4">
        <h2 className="text-base md:text-lg font-bold text-slate-200">Cost Comparison by Region</h2>
        <p className="text-xs text-slate-400 mt-1">30-day estimated costs</p>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 5, right: 20, bottom: 40, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="displayName"
              stroke="#64748b"
              fontSize={12}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#64748b"
              fontSize={12}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
              itemStyle={{ color: '#f59e0b' }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Cost']}
            />
            <Bar
              dataKey="cost"
              fill="#f59e0b"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {data.length === 0 && (
        <div className="h-64 flex items-center justify-center text-slate-400">
          No region data available
        </div>
      )}
    </div>
  );
}

export default memo(RegionComparisonChart);
