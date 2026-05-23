/**Sprint 34 Phase 4: Rule Management UI Tests

Tests for rule management UI components:
- RulesList display and actions
- RuleEditor modal for create/update
- AlertHistory timeline display
- AuditLogsDashboard tab switching
*/

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RulesList } from '@/components/Dashboard/RulesList';
import { RuleEditor } from '@/components/Dashboard/RuleEditor';
import { AlertHistory } from '@/components/Dashboard/AlertHistory';
import { AuditLogsDashboard } from '@/components/Dashboard/AuditLogsDashboard';

// Mock SWR hook
jest.mock('swr', () => ({
  __esModule: true,
  default: (key: string) => ({
    data: null,
    error: null,
    isLoading: false,
    mutate: jest.fn(),
  }),
}));

// Mock useSecurityRules hook
jest.mock('@/lib/hooks/useSecurityRules', () => ({
  useSecurityRules: () => ({
    rules: [
      {
        rule_id: 'rule-1',
        rule_type: 'connection_spike',
        condition: { threshold: 10, window_minutes: 5 },
        action: { notify: ['telegram'] },
        priority: 5,
        enabled: true,
        account_id: 'acc-1',
      },
    ],
    isLoading: false,
    error: null,
    createRule: jest.fn(),
    updateRule: jest.fn(),
    deleteRule: jest.fn(),
    mutate: jest.fn(),
  }),
}));

describe('Phase 4: Rule Management UI', () => {
  describe('RulesList Component', () => {
    test('renders rules table with columns', () => {
      render(<RulesList />);

      expect(screen.getByText('규칙 ID')).toBeInTheDocument();
      expect(screen.getByText('규칙 타입')).toBeInTheDocument();
      expect(screen.getByText('우선순위')).toBeInTheDocument();
      expect(screen.getByText('활성화')).toBeInTheDocument();
    });

    test('displays rule in table with correct data', () => {
      render(<RulesList />);

      expect(screen.getByText('rule-1')).toBeInTheDocument();
      expect(screen.getByText('connection_spike')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    test('shows action buttons for each rule', () => {
      render(<RulesList />);

      const editButtons = screen.getAllByRole('button', { name: /수정|edit/i });
      const deleteButtons = screen.getAllByRole('button', { name: /삭제|delete/i });

      expect(editButtons.length).toBeGreaterThan(0);
      expect(deleteButtons.length).toBeGreaterThan(0);
    });
  });

  describe('RuleEditor Component', () => {
    test('renders modal when isOpen is true', () => {
      render(
        <RuleEditor
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      expect(screen.getByText(/규칙 생성|Create Rule/i)).toBeInTheDocument();
    });

    test('does not render modal when isOpen is false', () => {
      const { container } = render(
        <RuleEditor
          isOpen={false}
          onClose={jest.fn()}
        />
      );

      const modal = container.querySelector('[role="dialog"]');
      expect(modal).not.toBeInTheDocument();
    });

    test('closes modal when close button clicked', () => {
      const onClose = jest.fn();
      render(
        <RuleEditor
          isOpen={true}
          onClose={onClose}
        />
      );

      const closeButton = screen.getByRole('button', { name: /닫기|close/i });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    test('shows rule type options in dropdown', () => {
      render(
        <RuleEditor
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const ruleTypeSelect = screen.getByDisplayValue(/connection_spike|규칙 타입/i);
      expect(ruleTypeSelect).toBeInTheDocument();
    });
  });

  describe('AlertHistory Component', () => {
    test('renders alert timeline with alerts', () => {
      const mockAlerts = [
        {
          alert_id: 'alert-1',
          rule_id: 'rule-1',
          severity: 9,
          message: 'Critical threat detected',
          timestamp: '2026-05-23T10:00:00Z',
          account_id: 'acc-1',
          status: 'sent',
        },
      ];

      render(<AlertHistory alerts={mockAlerts} />);

      expect(screen.getByText('Critical threat detected')).toBeInTheDocument();
    });

    test('displays severity indicator with correct emoji', () => {
      const mockAlerts = [
        {
          alert_id: 'alert-1',
          rule_id: 'rule-1',
          severity: 9,
          message: 'Critical alert',
          timestamp: '2026-05-23T10:00:00Z',
          account_id: 'acc-1',
          status: 'sent',
        },
      ];

      render(<AlertHistory alerts={mockAlerts} />);

      expect(screen.getByText(/🚨/)).toBeInTheDocument();
    });

    test('shows alert status indicator', () => {
      const mockAlerts = [
        {
          alert_id: 'alert-1',
          rule_id: 'rule-1',
          severity: 5,
          message: 'Test alert',
          timestamp: '2026-05-23T10:00:00Z',
          account_id: 'acc-1',
          status: 'sent',
        },
      ];

      render(<AlertHistory alerts={mockAlerts} />);

      const statusElements = screen.getAllByRole('img', { hidden: true });
      expect(statusElements.length).toBeGreaterThan(0);
    });
  });

  describe('AuditLogsDashboard Tab Switching', () => {
    test('renders both log and rules tabs', () => {
      render(<AuditLogsDashboard />);

      expect(screen.getByRole('button', { name: '감시 로그' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '규칙 관리' })).toBeInTheDocument();
    });

    test('shows logs tab content by default', () => {
      render(<AuditLogsDashboard />);

      expect(screen.getByText(/감시 로그/)).toBeInTheDocument();
    });

    test('switches to rules tab when clicked', async () => {
      render(<AuditLogsDashboard />);

      const rulesTab = screen.getByRole('button', { name: '규칙 관리' });
      fireEvent.click(rulesTab);

      await waitFor(() => {
        expect(screen.getByText(/\+ 규칙 추가/)).toBeInTheDocument();
      });
    });

    test('shows "add rule" button only on rules tab', async () => {
      render(<AuditLogsDashboard />);

      let addButton = screen.queryByText(/\+ 규칙 추가/);
      expect(addButton).not.toBeInTheDocument();

      const rulesTab = screen.getByRole('button', { name: '규칙 관리' });
      fireEvent.click(rulesTab);

      await waitFor(() => {
        addButton = screen.getByText(/\+ 규칙 추가/);
        expect(addButton).toBeInTheDocument();
      });
    });
  });
});
