import { test, expect } from '@playwright/test';

/**
 * Smoke suite - fast sanity check that the OMS-360 stack (app/main.py +
 * docker-compose services) is up and reachable before running the full
 * regression pack. Should complete in a few seconds.
 */

test.describe('Smoke @smoke', () => {
  test('root endpoint responds', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/');
    expect(res.ok()).toBeTruthy();
  });

  test('version endpoint responds', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/version');
    expect(res.ok()).toBeTruthy();
  });

  test('health endpoint reports a status', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/health');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('status');
    expect(body).toHaveProperty('dependencies');
  });

  test('metrics endpoint responds', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/metrics');
    expect(res.ok()).toBeTruthy();
  });

  test('orders list endpoint responds', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/api/v1/orders');
    expect(res.ok()).toBeTruthy();
  });

  test('inventory list endpoint responds', { tag: '@smoke' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory');
    expect(res.ok()).toBeTruthy();
  });

  test('Swagger UI (/docs) is reachable', { tag: '@smoke' }, async ({ page }) => {
    const res = await page.goto('/docs');
    expect(res?.ok()).toBeTruthy();
    await expect(page).toHaveTitle(/swagger|oms/i);
  });

  test('Operations dashboard page loads', { tag: '@smoke' }, async ({ page }) => {
    const res = await page.goto('/dashboard/operations');
    expect(res?.ok()).toBeTruthy();
  });

  test('Inventory dashboard page loads', { tag: '@smoke' }, async ({ page }) => {
    const res = await page.goto('/dashboard/inventory');
    expect(res?.ok()).toBeTruthy();
  });

  test('Monitoring dashboard page loads', { tag: '@smoke' }, async ({ page }) => {
    const res = await page.goto('/dashboard/monitoring');
    expect(res?.ok()).toBeTruthy();
  });

  test('AI Copilot dashboard page loads', { tag: '@smoke' }, async ({ page }) => {
    const res = await page.goto('/dashboard/ai-copilot');
    expect(res?.ok()).toBeTruthy();
  });
});
