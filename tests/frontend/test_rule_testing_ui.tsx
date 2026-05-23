/**Sprint 35 Phase 1: Rule Testing UI Tests

Tests for rule testing UI components:
- RuleTestModal rendering and interactions
- Test execution and result display
- Error handling
*/

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RuleTestModal } from '@/components/Dashboard/RuleTestModal';

// Mock fetch
global.fetch = jest.fn();

describe('Phase 1: Rule Testing UI', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('RuleTestModal Component', () => {
    const mockRule = {
      rule_id: 'rule-1',
      rule_type: 'connection_spike',
      condition: { threshold: 10, window_minutes: 5 },
      action: { notify: ['telegram'] },
      priority: 5,
    };

    test('renders modal when isOpen is true', () => {
      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      expect(screen.getByText(/규칙 테스트/)).toBeInTheDocument();
      expect(screen.getByText('connection_spike')).toBeInTheDocument();
    });

    test('does not render modal when isOpen is false', () => {
      const { container } = render(
        <RuleTestModal
          isOpen={false}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
    });

    test('displays rule information', () => {
      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      expect(screen.getByText('rule-1')).toBeInTheDocument();
      expect(screen.getByDisplayValue('acc-1')).toBeInTheDocument();
    });

    test('closes modal when close button clicked', () => {
      const onClose = jest.fn();
      render(
        <RuleTestModal
          isOpen={true}
          onClose={onClose}
          rule={mockRule}
        />
      );

      const closeButton = screen.getByRole('button', { name: /닫기/ });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    test('displays test button', () => {
      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      expect(screen.getByRole('button', { name: /테스트 실행/ })).toBeInTheDocument();
    });

    test('shows test results when test completes', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          rule_id: 'rule-1',
          total_logs: 10,
          matched_logs: 3,
          detected_threats: [
            {
              threat_id: 'threat-1',
              rule_id: 'rule-1',
              severity: 8,
              message: 'Rule triggered',
              evidence_count: 3,
            },
          ],
          execution_time_ms: 45.5,
        }),
      });

      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const testButton = screen.getByRole('button', { name: /테스트 실행/ });
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(screen.getByText(/테스트 결과/)).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });

    test('displays error message on test failure', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          error_message: 'Invalid rule format',
        }),
      });

      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const testButton = screen.getByRole('button', { name: /테스트 실행/ });
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid rule format/)).toBeInTheDocument();
      });
    });

    test('shows loading state during test execution', async () => {
      (global.fetch as jest.Mock).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({
              success: true,
              total_logs: 5,
              matched_logs: 2,
              detected_threats: [],
              execution_time_ms: 10,
            }),
          });
        }, 100))
      );

      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const testButton = screen.getByRole('button', { name: /테스트 실행/ });
      fireEvent.click(testButton);

      // Check for loading state
      await waitFor(() => {
        expect(screen.getByText(/테스트 실행 중/)).toBeInTheDocument();
      });

      // Wait for completion
      await waitFor(() => {
        expect(screen.getByText(/테스트 결과/)).toBeInTheDocument();
      });
    });

    test('allows account id to be changed', () => {
      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const accountInput = screen.getByDisplayValue('acc-1');
      fireEvent.change(accountInput, { target: { value: 'acc-2' } });

      expect(screen.getByDisplayValue('acc-2')).toBeInTheDocument();
    });

    test('displays threat details when detected', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          rule_id: 'rule-1',
          total_logs: 10,
          matched_logs: 5,
          detected_threats: [
            {
              threat_id: 'threat-1',
              rule_id: 'rule-1',
              severity: 9,
              message: 'Critical threat detected',
              evidence_count: 5,
            },
          ],
          execution_time_ms: 50,
        }),
      });

      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const testButton = screen.getByRole('button', { name: /테스트 실행/ });
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(screen.getByText(/탐지된 위협/)).toBeInTheDocument();
        expect(screen.getByText(/Critical threat detected/)).toBeInTheDocument();
        expect(screen.getByText(/심각도: 9/)).toBeInTheDocument();
      });
    });

    test('shows no matches message when no threats detected', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          rule_id: 'rule-1',
          total_logs: 10,
          matched_logs: 0,
          detected_threats: [],
          execution_time_ms: 40,
        }),
      });

      render(
        <RuleTestModal
          isOpen={true}
          onClose={jest.fn()}
          rule={mockRule}
        />
      );

      const testButton = screen.getByRole('button', { name: /테스트 실행/ });
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(screen.getByText(/규칙과 매칭된 로그가 없습니다/)).toBeInTheDocument();
      });
    });
  });
});
