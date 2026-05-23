/**
 * Sprint 35 Phase 3: Rule Rollback API Tests
 * Tests for rule rollback endpoints
 */

import { POST as rollbackRule } from '@/app/api/guardian/rules/[rule_id]/rollback/route';
import { GET as getVersions } from '@/app/api/guardian/rules/[rule_id]/versions/route';
import { NextRequest } from 'next/server';

describe('Rule Rollback API', () => {
  describe('POST /api/guardian/rules/[rule_id]/rollback', () => {
    it('should rollback to a previous version', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-123/rollback'),
        {
          method: 'POST',
          body: JSON.stringify({
            version_id: 'ver-1',
            rolled_back_by: 'test-user',
          }),
        }
      );

      const response = await rollbackRule(request, { params: { rule_id: 'rule-123' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.rule_id).toBe('rule-123');
      expect(data.previous_version_id).toBe('ver-1');
      expect(data.new_version_id).toBeDefined();
      expect(data.new_version_number).toBeDefined();
      expect(data.rolled_back_at).toBeDefined();
    });

    it('should reject invalid rule_id', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/invalid/rollback'),
        {
          method: 'POST',
          body: JSON.stringify({ version_id: 'ver-1' }),
        }
      );

      const response = await rollbackRule(request, { params: { rule_id: '[rule_id]' } });
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
    });

    it('should reject missing version_id', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-xyz/rollback'),
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      );

      const response = await rollbackRule(request, { params: { rule_id: 'rule-xyz' } });
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.error_message).toContain('version_id');
    });

    it('should return valid timestamp for rollback', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-abc/rollback'),
        {
          method: 'POST',
          body: JSON.stringify({
            version_id: 'ver-2',
          }),
        }
      );

      const response = await rollbackRule(request, { params: { rule_id: 'rule-abc' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.rolled_back_at).toBeDefined();
      expect(new Date(data.rolled_back_at).getTime()).toBeGreaterThan(0);
    });
  });

  describe('GET /api/guardian/rules/[rule_id]/versions', () => {
    it('should return version history', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-123/versions')
      );

      const response = await getVersions(request, { params: { rule_id: 'rule-123' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.rule_id).toBe('rule-123');
      expect(Array.isArray(data.versions)).toBe(true);
    });

    it('should reject invalid rule_id', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/invalid/versions')
      );

      const response = await getVersions(request, { params: { rule_id: '[rule_id]' } });
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
    });

    it('should respect limit parameter', async () => {
      const request = new NextRequest(
        new URL('http://localhost:3000/api/guardian/rules/rule-xyz/versions?limit=5')
      );

      const response = await getVersions(request, { params: { rule_id: 'rule-xyz' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(Array.isArray(data.versions)).toBe(true);
    });
  });
});
