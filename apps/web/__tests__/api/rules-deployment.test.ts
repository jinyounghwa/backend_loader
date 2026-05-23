/**
 * Sprint 35 Phase 2: Rule Deployment API Tests
 * Tests for rule deployment endpoints
 */

import { POST as deployRule } from '@/app/api/guardian/rules/[rule_id]/deploy/route';
import { NextRequest } from 'next/server';

describe('Rule Deployment API', () => {
  describe('POST /api/guardian/rules/[rule_id]/deploy', () => {
    it('should deploy a rule with ACTIVE status', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-123/deploy'),
        {
          method: 'POST',
          body: JSON.stringify({
            status: 'ACTIVE',
            deployed_by: 'test-user',
          }),
        }
      );

      const response = await deployRule(request, { params: { rule_id: 'rule-123' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.rule_id).toBe('rule-123');
      expect(data.deployment_id).toBeDefined();
      expect(data.status).toBe('ACTIVE');
    });

    it('should reject invalid rule_id', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/invalid/deploy'),
        {
          method: 'POST',
          body: JSON.stringify({ status: 'ACTIVE' }),
        }
      );

      const response = await deployRule(request, { params: { rule_id: '[rule_id]' } });
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
    });

    it('should return deployment metadata with timestamp', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-xyz/deploy'),
        {
          method: 'POST',
          body: JSON.stringify({
            status: 'ACTIVE',
            deployed_by: 'system',
          }),
        }
      );

      const response = await deployRule(request, { params: { rule_id: 'rule-xyz' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.deployment_date).toBeDefined();
      expect(typeof data.deployment_date).toBe('string');
      expect(new Date(data.deployment_date).getTime()).toBeGreaterThan(0);
    });

    it('should default to ACTIVE status', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-default/deploy'),
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      );

      const response = await deployRule(request, { params: { rule_id: 'rule-default' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.status).toBe('ACTIVE');
    });
  });
});
