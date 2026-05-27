import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area, AreaChart } from "recharts";

interface CostForecast {
  day: number;
  forecast: number;
  lower_bound: number;
  upper_bound: number;
  confidence: number;
}

interface CostTrendChartProps {
  forecasts: CostForecast[];
  title?: string;
  showBounds?: boolean;
}

export const CostTrendChart: React.FC<CostTrendChartProps> = ({
  forecasts,
  title = "Cost Trend Forecast",
  showBounds = true,
}) => {
  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="w-full h-96 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">No forecast data available</p>
      </div>
    );
  }

  const data = forecasts.map((f) => ({
    day: `Day ${f.day}`,
    forecast: f.forecast,
    lower: f.lower_bound,
    upper: f.upper_bound,
    confidence: f.confidence,
  }));

  return (
    <div className="w-full h-96 bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="day" />
          <YAxis />
          <Tooltip
            formatter={(value) => value.toFixed(2)}
            contentStyle={{ backgroundColor: "#fff", border: "1px solid #ccc", borderRadius: "4px" }}
          />
          <Legend />
          {showBounds && <Area type="monotone" dataKey="upper" stroke="none" fill="none" />}
          <Area type="monotone" dataKey="forecast" stroke="#3b82f6" fillOpacity={1} fill="url(#colorForecast)" />
          {showBounds && <Area type="monotone" dataKey="lower" stroke="none" fill="none" />}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CostTrendChart;
