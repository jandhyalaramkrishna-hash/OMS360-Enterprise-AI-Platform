import { test, expect } from '@playwright/test';

/**
 * app/routes/metrics.py - GET /metrics
 * In-memory + DB-backed application metrics (orders processed/failed/cancelled,
 * duplicate requests, Kafka publish/consume/retry/DLQ counts, API response
 * times, plus a `dlq` block backed by dlq_orders via get_dlq_summary()).
 */

test.describe('Metrics API @regression', () => {
  test('GET /metrics returns 200 with a JSON snapshot', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/metrics');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(typeof body).toBe('object');
  });

  test('GET /metrics snapshot includes a dlq summary block', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/metrics');
    const body = await res.json();
    expect(body).toHaveProperty('dlq');
  });

  test('GET /metrics is idempotent (repeated reads do not error)', { tag: '@regression' }, async ({ request }) => {
    for (let i = 0; i < 3; i++) {
      const res = await request.get('/metrics');
      expect(res.status()).toBe(200);
    }
  });
});
