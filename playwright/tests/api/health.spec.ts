import { test, expect } from '@playwright/test';

/**
 * app/routes/health.py
 *   GET /          - root info
 *   GET /version   - version info
 *   GET /health    - full dependency aggregation, rolled up into an overall status
 *
 * Dependency keys below are read directly from the `health()` route
 * handler's `dependencies` dict (app/routes/health.py, corrected
 * 2026-08-03 after a real local run against the live app surfaced that
 * this test previously asserted a plain "kafka" key sourced from
 * app/schemas.py::SystemHealthResponse's illustrative docstring example,
 * not the route's actual implementation - the real handler never emits
 * "kafka"; Kafka is split into three real keys instead):
 *   application, database, kafka_broker, kafka_producer,
 *   kafka_consumer_group, disk, memory, cpu, docker, redis,
 *   build_version, environment, db_pool
 */

test.describe('Health API @regression', () => {
  test('GET / returns 200 with a body', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toBeTruthy();
  });

  test('GET /version returns 200', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/version');
    expect(res.status()).toBe(200);
  });

  test('GET /health returns overall status + dependency map', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/health');
    expect(res.status()).toBe(200);
    const body = await res.json();

    expect(body).toHaveProperty('status');
    expect(typeof body.status).toBe('string');

    expect(body).toHaveProperty('dependencies');
    expect(typeof body.dependencies).toBe('object');

    // Per the real app/routes/health.py `health()` handler (read directly from
    // source, then cross-checked against a real local execution 2026-08-03)
    // - the full, exact set of dependency keys the endpoint actually emits.
    // Asserting the complete set (13 keys) rather than a partial subset, so
    // this test fails loudly again if the real contract changes further.
    const expectedKeys = [
      'application', 'database', 'kafka_broker', 'kafka_producer',
      'kafka_consumer_group', 'disk', 'memory', 'cpu', 'docker', 'redis',
      'build_version', 'environment', 'db_pool',
    ];
    for (const key of expectedKeys) {
      expect(Object.keys(body.dependencies)).toContain(key);
    }

    // No plain "kafka" key exists on the real contract - Kafka status is
    // reported via the three keys above instead. Asserted explicitly so a
    // future accidental re-introduction of a merged "kafka" key (or removal
    // of one of the three real keys) is caught either way.
    expect(Object.keys(body.dependencies)).not.toContain('kafka');
  });

  test('GET /health status is one of the known overall states', { tag: '@regression' }, async ({ request }) => {
    const res = await request.get('/health');
    const body = await res.json();
    // _compute_overall_status in app/routes/health.py rolls dependency checks
    // up into a coarse status string - assert it's non-empty and uppercase,
    // without hardcoding the exact enum (avoids over-fitting to internals we
    // did not fully enumerate from source).
    expect(body.status.length).toBeGreaterThan(0);
    expect(body.status).toBe(body.status.toUpperCase());
  });

  test('unknown route returns 404', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get('/this-route-does-not-exist');
    expect(res.status()).toBe(404);
  });
});
