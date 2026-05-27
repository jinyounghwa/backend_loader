import React, { useState, useMemo } from "react";
import { DollarSign, TrendingUp, Clock, CheckCircle, AlertCircle } from "lucide-react";

interface ROIResult {
  breakeven_available: boolean;
  upfront_cost: number;
  monthly_savings: number;
  breakeven_months: number;
  annual_benefit: number;
  roi_percent: number;
  payback_feasible: boolean;
}

interface ROICalculatorProps {
  title?: string;
  onCalculate?: (result: ROIResult) => void;
}

export const ROICalculator: React.FC<ROICalculatorProps> = ({ title = "ROI Calculator", onCalculate }) => {
  const [upfrontCost, setUpfrontCost] = useState<number>(5000);
  const [monthlySavings, setMonthlySavings] = useState<number>(500);

  const result: ROIResult = useMemo(() => {
    if (monthlySavings <= 0) {
      return {
        breakeven_available: false,
        upfront_cost: upfrontCost,
        monthly_savings: monthlySavings,
        breakeven_months: 0,
        annual_benefit: 0,
        roi_percent: 0,
        payback_feasible: false,
      };
    }

    const breakeven_months = upfrontCost / monthlySavings;
    const annual_benefit = monthlySavings * 12 - upfrontCost;
    const roi_percent = upfrontCost > 0 ? (annual_benefit / upfrontCost) * 100 : 0;

    return {
      breakeven_available: true,
      upfront_cost: upfrontCost,
      monthly_savings: monthlySavings,
      breakeven_months,
      annual_benefit,
      roi_percent,
      payback_feasible: breakeven_months < 36,
    };
  }, [upfrontCost, monthlySavings]);

  React.useEffect(() => {
    if (result.breakeven_available && onCalculate) {
      onCalculate(result);
    }
  }, [result, onCalculate]);

  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <DollarSign className="w-5 h-5" />
        {title}
      </h3>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Upfront Cost ($)</label>
          <input
            type="number"
            value={upfrontCost}
            onChange={(e) => setUpfrontCost(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            min="0"
            step="100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Monthly Savings ($)</label>
          <input
            type="number"
            value={monthlySavings}
            onChange={(e) => setMonthlySavings(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            min="0"
            step="50"
          />
        </div>
      </div>

      {result.breakeven_available && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-medium text-blue-600">Break-Even Period</span>
              </div>
              <p className="text-2xl font-bold text-blue-900">{result.breakeven_months.toFixed(1)} months</p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-green-600" />
                <span className="text-xs font-medium text-green-600">Annual Benefit</span>
              </div>
              <p className="text-2xl font-bold text-green-900">${result.annual_benefit.toFixed(0)}</p>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <span className="text-xs font-medium text-purple-600">ROI Percentage</span>
              <p className="text-2xl font-bold text-purple-900">{result.roi_percent.toFixed(1)}%</p>
            </div>

            <div className={`border rounded-lg p-4 ${result.payback_feasible ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="flex items-center gap-2 mb-1">
                {result.payback_feasible ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-600" />
                )}
                <span className={`text-xs font-medium ${result.payback_feasible ? "text-green-600" : "text-red-600"}`}>
                  Feasibility
                </span>
              </div>
              <p className={`text-2xl font-bold ${result.payback_feasible ? "text-green-900" : "text-red-900"}`}>
                {result.payback_feasible ? "Feasible" : "Not Feasible"}
              </p>
            </div>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-2">Investment Summary</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-700">Monthly Savings:</span>
                <span className="font-medium text-gray-900">${result.monthly_savings.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-700">Annual Savings:</span>
                <span className="font-medium text-gray-900">${(result.monthly_savings * 12).toFixed(2)}</span>
              </div>
              <div className="flex justify-between border-t border-gray-300 pt-2">
                <span className="text-gray-700">Net First Year Benefit:</span>
                <span className="font-medium text-gray-900">${result.annual_benefit.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {!result.breakeven_available && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">Invalid input: Monthly savings must be greater than 0</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ROICalculator;
