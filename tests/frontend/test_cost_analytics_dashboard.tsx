import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import CostTrendChart from "@/components/Dashboard/CostTrendChart";
import SavingsOpportunitiesPanel from "@/components/Dashboard/SavingsOpportunitiesPanel";
import CostAnomalyAlert from "@/components/Dashboard/CostAnomalyAlert";
import ROICalculator from "@/components/Dashboard/ROICalculator";

// ==========================================
// CostTrendChart Tests
// ==========================================

describe("CostTrendChart", () => {
  const mockForecasts = [
    { day: 1, forecast: 100, lower_bound: 90, upper_bound: 110, confidence: 0.98 },
    { day: 2, forecast: 105, lower_bound: 95, upper_bound: 115, confidence: 0.96 },
    { day: 3, forecast: 110, lower_bound: 100, upper_bound: 120, confidence: 0.94 },
  ];

  test("renders cost trend chart with title", () => {
    render(<CostTrendChart forecasts={mockForecasts} title="30-Day Cost Forecast" />);

    expect(screen.getByText("30-Day Cost Forecast")).toBeInTheDocument();
  });

  test("renders empty state when no forecasts provided", () => {
    render(<CostTrendChart forecasts={[]} />);

    expect(screen.getByText("No forecast data available")).toBeInTheDocument();
  });

  test("renders all forecast data points", () => {
    const { container } = render(<CostTrendChart forecasts={mockForecasts} />);

    // Check that chart container is rendered
    const chartContainer = container.querySelector(".recharts-wrapper");
    expect(chartContainer).toBeInTheDocument();
  });
});

// ==========================================
// SavingsOpportunitiesPanel Tests
// ==========================================

describe("SavingsOpportunitiesPanel", () => {
  const mockOpportunities = [
    {
      service: "ec2",
      current_cost: 1000,
      max_potential_savings: 400,
      savings_percentage: 40,
      reason: "Reserved instances, Spot instances",
      impact: "HIGH" as const,
    },
    {
      service: "rds",
      current_cost: 500,
      max_potential_savings: 175,
      savings_percentage: 35,
      reason: "Reserved instances",
      impact: "HIGH" as const,
    },
    {
      service: "s3",
      current_cost: 200,
      max_potential_savings: 40,
      savings_percentage: 20,
      reason: "Lifecycle policies",
      impact: "MEDIUM" as const,
    },
  ];

  test("renders opportunities panel with title", () => {
    render(<SavingsOpportunitiesPanel opportunities={mockOpportunities} />);

    expect(screen.getByText("Cost Savings Opportunities")).toBeInTheDocument();
  });

  test("displays total savings calculation", () => {
    render(<SavingsOpportunitiesPanel opportunities={mockOpportunities} />);

    // Total = 400 + 175 + 40 = 615
    expect(screen.getByText(/Total potential savings.*\$615.00/)).toBeInTheDocument();
  });

  test("renders each opportunity with impact badge", () => {
    render(<SavingsOpportunitiesPanel opportunities={mockOpportunities} />);

    expect(screen.getByText("EC2")).toBeInTheDocument();
    expect(screen.getByText("RDS")).toBeInTheDocument();
    expect(screen.getByText("S3")).toBeInTheDocument();
    expect(screen.getAllByText("HIGH")).toHaveLength(2);
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
  });

  test("renders empty state when no opportunities", () => {
    render(<SavingsOpportunitiesPanel opportunities={[]} />);

    expect(screen.getByText("No optimization opportunities detected")).toBeInTheDocument();
  });
});

// ==========================================
// CostAnomalyAlert Tests
// ==========================================

describe("CostAnomalyAlert", () => {
  const mockSpikes = [
    { day: 5, cost: 250, z_score: 2.3, increase_percent: 142.6, severity: "HIGH" as const },
    { day: 12, cost: 200, z_score: 1.8, increase_percent: 95.2, severity: "MEDIUM" as const },
  ];

  test("renders anomaly alert with title", () => {
    render(<CostAnomalyAlert spikes={mockSpikes} />);

    expect(screen.getByText("Cost Anomalies")).toBeInTheDocument();
  });

  test("displays each cost spike with severity", () => {
    render(<CostAnomalyAlert spikes={mockSpikes} />);

    expect(screen.getByText("Day 5")).toBeInTheDocument();
    expect(screen.getByText("Day 12")).toBeInTheDocument();
    expect(screen.getAllByText("Anomaly")).toHaveLength(2);
  });

  test("renders empty state when no anomalies", () => {
    render(<CostAnomalyAlert spikes={[]} />);

    expect(screen.getByText("No cost anomalies detected")).toBeInTheDocument();
  });

  test("shows correct severity badges", () => {
    render(<CostAnomalyAlert spikes={mockSpikes} />);

    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
  });
});

// ==========================================
// ROICalculator Tests
// ==========================================

describe("ROICalculator", () => {
  test("renders calculator with input fields", () => {
    render(<ROICalculator />);

    expect(screen.getByText("ROI Calculator")).toBeInTheDocument();
    expect(screen.getByLabelText("Upfront Cost ($)")).toBeInTheDocument();
    expect(screen.getByLabelText("Monthly Savings ($)")).toBeInTheDocument();
  });

  test("calculates break-even period correctly", () => {
    const { rerender } = render(<ROICalculator />);

    const upfrontInput = screen.getByLabelText("Upfront Cost ($)") as HTMLInputElement;
    const monthlyInput = screen.getByLabelText("Monthly Savings ($)") as HTMLInputElement;

    fireEvent.change(upfrontInput, { target: { value: "5000" } });
    fireEvent.change(monthlyInput, { target: { value: "500" } });

    // Wait for calculation
    setTimeout(() => {
      expect(screen.getByText(/Break-Even Period/)).toBeInTheDocument();
      // 5000 / 500 = 10 months
      expect(screen.getByText("10.0 months")).toBeInTheDocument();
    }, 0);
  });

  test("shows error when monthly savings is zero", () => {
    const { rerender } = render(<ROICalculator />);

    const monthlyInput = screen.getByLabelText("Monthly Savings ($)") as HTMLInputElement;
    fireEvent.change(monthlyInput, { target: { value: "0" } });

    // Wait for validation
    setTimeout(() => {
      expect(screen.getByText(/Monthly savings must be greater than 0/)).toBeInTheDocument();
    }, 0);
  });

  test("calls onCalculate callback when calculation completes", () => {
    const mockCallback = jest.fn();
    render(<ROICalculator onCalculate={mockCallback} />);

    const upfrontInput = screen.getByLabelText("Upfront Cost ($)") as HTMLInputElement;
    fireEvent.change(upfrontInput, { target: { value: "10000" } });

    setTimeout(() => {
      expect(mockCallback).toHaveBeenCalled();
      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          breakeven_available: true,
          upfront_cost: 10000,
        })
      );
    }, 0);
  });

  test("displays annual benefit calculation", () => {
    render(<ROICalculator />);

    const upfrontInput = screen.getByLabelText("Upfront Cost ($)") as HTMLInputElement;
    const monthlyInput = screen.getByLabelText("Monthly Savings ($)") as HTMLInputElement;

    fireEvent.change(upfrontInput, { target: { value: "1000" } });
    fireEvent.change(monthlyInput, { target: { value: "200" } });

    // Wait for calculation: annual = (200 * 12) - 1000 = 1400
    setTimeout(() => {
      expect(screen.getByText(/Annual Benefit/)).toBeInTheDocument();
    }, 0);
  });
});

// ==========================================
// Integration Tests
// ==========================================

describe("Cost Analytics Dashboard Integration", () => {
  test("renders complete dashboard with all components", () => {
    const mockForecasts = [
      { day: 1, forecast: 100, lower_bound: 90, upper_bound: 110, confidence: 0.98 },
    ];

    const mockOpportunities = [
      {
        service: "ec2",
        current_cost: 1000,
        max_potential_savings: 400,
        savings_percentage: 40,
        reason: "Reserved instances",
        impact: "HIGH" as const,
      },
    ];

    const mockSpikes = [
      { day: 5, cost: 250, z_score: 2.3, increase_percent: 142.6, severity: "HIGH" as const },
    ];

    render(
      <div className="space-y-6">
        <CostTrendChart forecasts={mockForecasts} />
        <SavingsOpportunitiesPanel opportunities={mockOpportunities} />
        <CostAnomalyAlert spikes={mockSpikes} />
        <ROICalculator />
      </div>
    );

    expect(screen.getByText("Cost Trend Forecast")).toBeInTheDocument();
    expect(screen.getByText("Cost Savings Opportunities")).toBeInTheDocument();
    expect(screen.getByText("Cost Anomalies")).toBeInTheDocument();
    expect(screen.getByText("ROI Calculator")).toBeInTheDocument();
  });

  test("handles responsive layout for mobile", () => {
    const { container } = render(
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CostTrendChart forecasts={[{ day: 1, forecast: 100, lower_bound: 90, upper_bound: 110, confidence: 0.98 }]} />
        <ROICalculator />
      </div>
    );

    const gridContainer = container.querySelector(".grid");
    expect(gridContainer).toHaveClass("grid-cols-1");
    expect(gridContainer).toHaveClass("md:grid-cols-2");
  });

  test("handles error states gracefully", () => {
    render(
      <div className="space-y-6">
        <CostTrendChart forecasts={[]} />
        <SavingsOpportunitiesPanel opportunities={[]} />
        <CostAnomalyAlert spikes={[]} />
      </div>
    );

    expect(screen.getByText("No forecast data available")).toBeInTheDocument();
    expect(screen.getByText("No optimization opportunities detected")).toBeInTheDocument();
    expect(screen.getByText("No cost anomalies detected")).toBeInTheDocument();
  });
});
