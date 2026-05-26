import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ThreatPredictionPanel from '@/components/Dashboard/ThreatPredictionPanel';
import AnomalyClusterPanel from '@/components/Dashboard/AnomalyClusterPanel';
import ThreatTrendChart from '@/components/Dashboard/ThreatTrendChart';
import PatternRecognitionPanel from '@/components/Dashboard/PatternRecognitionPanel';

// Mock fetch
global.fetch = jest.fn();

describe('ThreatPredictionPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders prediction panel with input', () => {
    render(<ThreatPredictionPanel />);

    expect(screen.getByText('Threat Predictions (7-Day)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter account ID')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Predict/i })).toBeInTheDocument();
  });

  test('displays predictions after successful fetch', async () => {
    const mockResponse = {
      predictions: [
        { date: '2026-05-27', expected_threats: 2.5, confidence: 0.95 },
        { date: '2026-05-28', expected_threats: 2.3, confidence: 0.93 }
      ],
      trend: 'stable',
      anomaly_score: 0.5,
      model_accuracy: 0.85
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<ThreatPredictionPanel />);

    const input = screen.getByPlaceholderText('Enter account ID');
    const button = screen.getByRole('button', { name: /Predict/i });

    fireEvent.change(input, { target: { value: 'test-account' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Model Accuracy')).toBeInTheDocument();
    });

    expect(screen.getByText('stable')).toBeInTheDocument();
    expect(screen.getByText('85.0%')).toBeInTheDocument();
  });

  test('displays error on failed prediction', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false
    });

    render(<ThreatPredictionPanel />);

    const input = screen.getByPlaceholderText('Enter account ID');
    const button = screen.getByRole('button', { name: /Predict/i });

    fireEvent.change(input, { target: { value: 'test-account' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch predictions/i)).toBeInTheDocument();
    });
  });
});

describe('AnomalyClusterPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders cluster panel with threat input', () => {
    render(<AnomalyClusterPanel />);

    expect(screen.getByText('Anomaly Clustering')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Add Threat \(JSON\)/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add/i })).toBeInTheDocument();
  });

  test('adds threat to list and performs clustering', async () => {
    const mockResponse = {
      clusters: [
        {
          id: 'C1',
          threats: ['t1'],
          threat_count: 1,
          cohesion: 0.95,
          avg_severity: 8.0
        }
      ],
      silhouette_score: 0.8,
      cluster_count: 1,
      threat_count: 1
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<AnomalyClusterPanel />);

    const textarea = screen.getByPlaceholderText(/Add Threat \(JSON\)/i);
    const addButton = screen.getByRole('button', { name: /Add/i });

    const threatJson = JSON.stringify({
      threat_id: 't1',
      severity: 8,
      account_risk_score: 0.8,
      event_frequency: 5,
      resource_impact_count: 3,
      response_time_seconds: 120,
      remediation_success_rate: 0.7
    });

    fireEvent.change(textarea, { target: { value: threatJson } });
    fireEvent.click(addButton);

    expect(screen.getByText('1 threat(s) added')).toBeInTheDocument();

    const clusterButton = screen.getByRole('button', { name: /Perform Clustering/i });
    fireEvent.click(clusterButton);

    await waitFor(() => {
      expect(screen.getByText('Clusters Created')).toBeInTheDocument();
    });

    expect(screen.getByText('0.80')).toBeInTheDocument();
  });

  test('shows error for invalid JSON', () => {
    render(<AnomalyClusterPanel />);

    const textarea = screen.getByPlaceholderText(/Add Threat \(JSON\)/i);
    const addButton = screen.getByRole('button', { name: /Add/i });

    fireEvent.change(textarea, { target: { value: 'invalid json' } });
    fireEvent.click(addButton);

    expect(screen.getByText('Invalid JSON format')).toBeInTheDocument();
  });
});

describe('ThreatTrendChart', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders trend chart with account input', () => {
    render(<ThreatTrendChart />);

    expect(screen.getByText('Threat Trends')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter account ID')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Analyze/i })).toBeInTheDocument();
  });

  test('displays trends after successful fetch', async () => {
    const mockResponse = {
      hourly_breakdown: [
        { hour: '2026-05-26T00', threats: 5, avg_severity: 6.2 },
        { hour: '2026-05-26T01', threats: 3, avg_severity: 5.8 }
      ],
      daily_breakdown: [],
      peak_hours: ['2026-05-26T00'],
      safe_hours: ['2026-05-26T02'],
      anomaly_hours: [],
      trend: 'stable',
      time_range: '24h'
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<ThreatTrendChart />);

    const input = screen.getByPlaceholderText('Enter account ID');
    const button = screen.getByRole('button', { name: /Analyze/i });

    fireEvent.change(input, { target: { value: 'test-account' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Peak Hours')).toBeInTheDocument();
    });

    expect(screen.getByText('Safe Hours')).toBeInTheDocument();
  });

  test('allows time range selection', () => {
    render(<ThreatTrendChart />);

    const select = screen.getByDisplayValue('Last 24h');
    expect(select).toBeInTheDocument();

    fireEvent.change(select, { target: { value: '7d' } });
    expect(screen.getByDisplayValue('Last 7d')).toBeInTheDocument();
  });
});

describe('PatternRecognitionPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders pattern panel with threat input', () => {
    render(<PatternRecognitionPanel />);

    expect(screen.getByText('Pattern Recognition')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Threat Sequence/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Identify Patterns/i })).toBeInTheDocument();
  });

  test('identifies patterns from threat sequence', async () => {
    const mockResponse = {
      patterns: [
        {
          id: 'P1',
          sequence: ['Unknown Region', 'Unauthorized SSH'],
          support: 0.4,
          confidence: 0.8,
          lift: 2.0,
          occurrences: 2
        }
      ],
      total_patterns: 1,
      threat_count: 5
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<PatternRecognitionPanel />);

    const textarea = screen.getByPlaceholderText(/Threat Sequence/i);
    const threat1 = JSON.stringify({ threat_type: 'Unknown Region', timestamp: '2026-05-26T00:00:00' });
    const threat2 = JSON.stringify({ threat_type: 'Unauthorized SSH', timestamp: '2026-05-26T01:00:00' });

    fireEvent.change(textarea, { target: { value: `${threat1}\n${threat2}` } });

    const button = screen.getByRole('button', { name: /Identify Patterns/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Patterns Found')).toBeInTheDocument();
    });

    expect(screen.getByText('P1')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
  });

  test('allows minimum support adjustment', () => {
    render(<PatternRecognitionPanel />);

    const slider = screen.getByRole('slider');
    expect(slider).toHaveValue('0.3');

    fireEvent.change(slider, { target: { value: '0.5' } });
    expect(slider).toHaveValue('0.5');
  });
});
