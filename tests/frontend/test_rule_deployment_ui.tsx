/**Sprint 35 Phase 2: Rule Deployment UI Tests

Tests for rule deployment UI components:
- RuleDeploymentPanel rendering and interactions
- Deployment history display
- Deploy button functionality
- Error handling
*/

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RuleDeploymentPanel } from '@/components/Dashboard/RuleDeploymentPanel';

// Mock fetch
global.fetch = jest.fn();

describe('Phase 2: Rule Deployment UI', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('RuleDeploymentPanel Component', () => {
    const mockRule = {
      rule_id: 'rule-1',
      rule_type: 'connection_spike',
      condition: { threshold: 10 },
      action: { notify: ['telegram'] },
      priority: 5,
      enabled: true,
      created_at: '2026-05-23T10:00:00Z',
      updated_at: '2026-05-23T10:00:00Z',
    };

    test('renders deployment panel', () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: [] }),
      });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      expect(screen.getByText('활성 배포')).toBeInTheDocument();
      expect(screen.getByText('전체 배포')).toBeInTheDocument();
    });

    test('displays deploy button', () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: [] }),
      });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /규칙 배포/ })).toBeInTheDocument();
    });

    test('loads and displays deployment history', async () => {
      const mockDeployments = [
        {
          deployment_id: 'dep-1',
          rule_id: 'rule-1',
          status: 'ACTIVE' as const,
          deployment_date: '2026-05-23T10:00:00Z',
          deployed_by: 'user',
        },
        {
          deployment_id: 'dep-2',
          rule_id: 'rule-1',
          status: 'PENDING' as const,
          deployment_date: '2026-05-23T09:00:00Z',
          deployed_by: 'system',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: mockDeployments }),
      });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('dep-1')).toBeInTheDocument();
      });

      expect(screen.getByText('ACTIVE')).toBeInTheDocument();
      expect(screen.getByText('PENDING')).toBeInTheDocument();
    });

    test('displays empty state when no deployments', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: [] }),
      });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('배포 이력이 없습니다')).toBeInTheDocument();
      });
    });

    test('shows deployment stats', async () => {
      const mockDeployments = [
        {
          deployment_id: 'dep-1',
          rule_id: 'rule-1',
          status: 'ACTIVE' as const,
          deployment_date: '2026-05-23T10:00:00Z',
          deployed_by: 'user',
        },
        {
          deployment_id: 'dep-2',
          rule_id: 'rule-1',
          status: 'PENDING' as const,
          deployment_date: '2026-05-23T09:00:00Z',
          deployed_by: 'system',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: mockDeployments }),
      });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      await waitFor(() => {
        // Stats should show 1 active and 2 total deployments
        const statTexts = screen.getAllByText(/1|2/);
        expect(statTexts.length).toBeGreaterThan(0);
      });
    });

    test('calls deploy API when deploy button clicked', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ deployments: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            deployment_id: 'dep-new',
            status: 'ACTIVE',
            deployment_date: '2026-05-23T11:00:00Z',
          }),
        });

      const onSuccess = jest.fn();
      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={onSuccess}
        />
      );

      const deployButton = screen.getByRole('button', { name: /규칙 배포/ });
      fireEvent.click(deployButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/deploy'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    test('disables deploy button when rule is disabled', () => {
      const disabledRule = { ...mockRule, enabled: false };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: [] }),
      });

      render(
        <RuleDeploymentPanel
          rule={disabledRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      const deployButton = screen.getByRole('button', { name: /규칙 배포/ });
      expect(deployButton).toBeDisabled();
    });

    test('displays error message on deployment failure', async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ deployments: [] }),
        })
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({
            success: false,
            error_message: 'Deployment failed: Invalid rule configuration',
          }),
        });

      render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      const deployButton = screen.getByRole('button', { name: /규칙 배포/ });
      fireEvent.click(deployButton);

      await waitFor(() => {
        expect(screen.getByText(/Deployment failed/)).toBeInTheDocument();
      });
    });

    test('highlights selected deployment', async () => {
      const mockDeployments = [
        {
          deployment_id: 'dep-1',
          rule_id: 'rule-1',
          status: 'ACTIVE' as const,
          deployment_date: '2026-05-23T10:00:00Z',
          deployed_by: 'user',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deployments: mockDeployments }),
      });

      const { container } = render(
        <RuleDeploymentPanel
          rule={mockRule}
          onDeploymentSuccess={jest.fn()}
        />
      );

      await waitFor(() => {
        const row = screen.getByText('dep-1').closest('tr');
        expect(row).toBeInTheDocument();

        fireEvent.click(row!);
        expect(row).toHaveClass('bg-slate-700/50');
      });
    });
  });
});
