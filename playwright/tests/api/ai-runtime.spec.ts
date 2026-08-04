import { test, expect } from '@playwright/test';

/**
 * app/api/ai/router.py - prefix /api/v1/ai, tags=["AI Runtime"]
 *   GET /health
 *   GET /config
 *   GET /providers
 *   GET /features
 *   GET /metrics
 *   GET /status
 *   GET /platform/health
 *
 * These are read-only diagnostic endpoints for the AI runtime layer
 * (independent of the AI Copilot feature router). No request bodies.
 */

const READ_ONLY_ENDPOINTS = [
  '/api/v1/ai/health',
  '/api/v1/ai/config',
  '/api/v1/ai/providers',
  '/api/v1/ai/features',
  '/api/v1/ai/metrics',
  '/api/v1/ai/status',
  '/api/v1/ai/platform/health',
];

test.describe('AI Runtime API @regression', () => {
  for (const endpoint of READ_ONLY_ENDPOINTS) {
    test(`GET ${endpoint} responds without a server error`, { tag: '@positive' }, async ({ request }) => {
      const res = await request.get(endpoint);
      // AI runtime may be intentionally disabled/unconfigured in some
      // environments (ai_enabled flag) - a graceful 2xx/4xx is acceptable,
      // a 5xx is not. We do not guess the exact body shape here since the
      // runtime feature-flag state was not read from source for this pass.
      expect(res.status()).toBeLessThan(500);
    });
  }

  test('GET /api/v1/ai/health returns JSON', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/ai/health');
    expect(res.status()).toBeLessThan(500);
    const body = await res.json().catch(() => null);
    expect(body).not.toBeNull();
  });

  test('GET /api/v1/ai/platform/health returns JSON', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/ai/platform/health');
    expect(res.status()).toBeLessThan(500);
    const body = await res.json().catch(() => null);
    expect(body).not.toBeNull();
  });

  test('unknown AI runtime route returns 404', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get('/api/v1/ai/does-not-exist');
    expect(res.status()).toBe(404);
  });
});
