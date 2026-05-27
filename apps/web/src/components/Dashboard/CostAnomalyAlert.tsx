import React from "react";
import { AlertTriangle, Zap } from "lucide-react";

interface CostSpike {
  day: number;
  cost: number;
  z_score: number;
  increase_percent: number;
  severity: "HIGH" | "MEDIUM";
}

interface CostAnomalyAlertProps {
  spikes: CostSpike[];
  title?: string;
}

const severityColors = {
  HIGH: "bg-red-50 border-red-200",
  MEDIUM: "bg-yellow-50 border-yellow-200",
};

const severityBadgeColors = {
  HIGH: "bg-red-100 text-red-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
};

export const CostAnomalyAlert: React.FC<CostAnomalyAlertProps> = ({ spikes, title = "Cost Anomalies" }) => {
  if (!spikes || spikes.length === 0) {
    return (
      <div className="w-full bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-green-600" />
          <p className="text-green-700">No cost anomalies detected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          {title}
        </h3>
      </div>

      <div className="space-y-3">
        {spikes.map((spike) => (
          <div key={spike.day} className={`border rounded-lg p-3 ${severityColors[spike.severity]}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">Day {spike.day}</span>
                <span className={`px-2 py-1 text-xs font-semibold rounded ${severityBadgeColors[spike.severity]}`}>
                  {spike.severity}
                </span>
              </div>
              <span className="text-sm font-semibold text-gray-900">${spike.cost.toFixed(2)}</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-gray-600">Z-Score:</span>
                <p className="font-medium text-gray-900">{spike.z_score.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-600">Increase:</span>
                <p className="font-medium text-gray-900">{spike.increase_percent.toFixed(1)}%</p>
              </div>
              <div>
                <span className="text-gray-600">Status:</span>
                <p className="font-medium text-red-600">Anomaly</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CostAnomalyAlert;
