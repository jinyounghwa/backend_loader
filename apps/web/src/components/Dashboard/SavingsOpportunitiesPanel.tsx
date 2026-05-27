import React from "react";
import { TrendingDown, AlertCircle, CheckCircle } from "lucide-react";

interface Opportunity {
  service: string;
  current_cost: number;
  max_potential_savings: number;
  savings_percentage: number;
  reason: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
}

interface SavingsOpportunitiesPanelProps {
  opportunities: Opportunity[];
  title?: string;
}

const impactColors = {
  HIGH: "bg-red-50 border-red-200",
  MEDIUM: "bg-yellow-50 border-yellow-200",
  LOW: "bg-blue-50 border-blue-200",
};

const impactBadgeColors = {
  HIGH: "bg-red-100 text-red-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  LOW: "bg-blue-100 text-blue-800",
};

export const SavingsOpportunitiesPanel: React.FC<SavingsOpportunitiesPanelProps> = ({
  opportunities,
  title = "Cost Savings Opportunities",
}) => {
  if (!opportunities || opportunities.length === 0) {
    return (
      <div className="w-full bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <p className="text-green-700">No optimization opportunities detected</p>
        </div>
      </div>
    );
  }

  const totalSavings = opportunities.reduce((sum, opp) => sum + opp.max_potential_savings, 0);

  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <TrendingDown className="w-4 h-4" />
          <span>Total potential savings: ${totalSavings.toFixed(2)}/month</span>
        </div>
      </div>

      <div className="space-y-3">
        {opportunities.map((opp) => (
          <div key={opp.service} className={`border rounded-lg p-3 ${impactColors[opp.impact]}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900 capitalize">{opp.service.replace(/_/g, " ")}</h4>
                <span className={`px-2 py-1 text-xs font-semibold rounded ${impactBadgeColors[opp.impact]}`}>
                  {opp.impact}
                </span>
              </div>
              <span className="text-sm font-semibold text-gray-900">${opp.max_potential_savings.toFixed(2)}</span>
            </div>

            <p className="text-xs text-gray-600 mb-2">{opp.reason}</p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-600">Current Cost:</span>
                <p className="font-medium text-gray-900">${opp.current_cost.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-600">Savings Potential:</span>
                <p className="font-medium text-gray-900">{opp.savings_percentage.toFixed(1)}%</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SavingsOpportunitiesPanel;
