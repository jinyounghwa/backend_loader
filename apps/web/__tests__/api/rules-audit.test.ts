/**
 * Sprint 35 Phase 4: Rule Audit Logs API Tests
 * Tests for rule audit logging endpoints
 */

import { GET as getAuditLogs } from '@/app/api/guardian/rules/audit/route';
import { NextRequest } from 'next/server';

describe('Rule Audit Logs API', () => {
  describe('GET /api/guardian/rules/audit', () => {
    it('should return audit logs for a rule', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/audit?rule_id=rule-123')
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(Array.isArray(data.logs)).toBe(true);
      expect(data.summary).toBeDefined();
      expect(data.summary.total_logs).toBeDefined();
      expect(data.summary.action_counts).toBeDefined();
      expect(data.summary.status_counts).toBeDefined();
    });

    it('should reject missing rule_id parameter', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/audit')
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error_message).toContain('rule_id');
    });

    it('should respect limit parameter', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/audit?rule_id=rule-xyz&limit=10')
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(Array.isArray(data.logs)).toBe(true);
    });

    it('should filter by action type', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/audit?rule_id=rule-abc&action=DEPLOY')
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(Array.isArray(data.logs)).toBe(true);
    });

    it('should include action summary in response', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/audit?rule_id=rule-summary')
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.summary).toBeDefined();
      expect(typeof data.summary.total_logs).toBe('number');
      expect(typeof data.summary.action_counts).toBe('object');
      expect(typeof data.summary.status_counts).toBe('object');
    });

    it('should handle time range filtering', async () => {
      const startTime = '2026-05-23T00:00:00Z';
      const endTime = '2026-05-24T00:00:00Z';

      const request = new NextRequest(
        new URL(
          `http://localhost:3000/api/guardian/rules/audit?rule_id=rule-time&start_time=${startTime}&end_time=${endTime}`
        )
      );

      const response = await getAuditLogs(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
    });
  });
});
