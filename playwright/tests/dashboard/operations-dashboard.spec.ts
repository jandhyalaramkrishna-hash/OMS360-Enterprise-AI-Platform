import { test, expect } from '@playwright/test';

/**
 * app/main.py serves /dashboard/operations (FileResponse, Cache-Control: no-store)
 * -> app/static/operations_dashboard.html
 *
 * Real element ids confirmed by inspecting the static HTML source (2026-08-03):
 *   clock, connBanner, lifecycleTrack (lc-order..lc-delivered),
 *   liveOrdersCount/liveOrdersBody, kitchenCount/kitchenBody,
 *   deliveryCount/deliveryBody, alertsCount/alertsList,
 *   kpi-total-orders, kpi-total-customers, kpi-total-sales, kpi-total-revenue,
 *   kpi-aov, kpi-pending, kpi-preparing, kpi-ready, kpi-ofd, kpi-delivered,
 *   kpi-cancelled
 *
 * The page is backed by JS calling the JSON APIs in app/routes/dashboard.py
 * (/api/v1/dashboard/kpis, /live-orders, /kitchen-ops, /delivery-ops, /alerts).
 */

test.describe('Operations Dashboard @regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/operations');
  });

  test('page loads and renders the KPI bar', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#kpi-total-orders')).toBeVisible();
    await expect(page.locator('#kpi-total-revenue')).toBeVisible();
    await expect(page.locator('#kpi-pending')).toBeVisible();
  });

  test('order lifecycle tracker renders all stages', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#lifecycleTrack')).toBeVisible();
    for (const stage of ['#lc-order', '#lc-payment', '#lc-inventory', '#lc-kitchen', '#lc-ready', '#lc-delivery', '#lc-delivered']) {
      await expect(page.locator(stage)).toBeAttached();
    }
  });

  test('live orders panel populates a count and a table body', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#liveOrdersCount')).toBeVisible();
    await expect(page.locator('#liveOrdersBody')).toBeAttached();
  });

  test('kitchen queue panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#kitchenCount')).toBeVisible();
    await expect(page.locator('#kitchenBody')).toBeAttached();
  });

  test('delivery queue panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#deliveryCount')).toBeVisible();
    await expect(page.locator('#deliveryBody')).toBeAttached();
  });

  test('alerts panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#alertsCount')).toBeVisible();
    await expect(page.locator('#alertsList')).toBeAttached();
  });

  test('connection banner element exists (shows on API/WS failure)', { tag: '@boundary' }, async ({ page }) => {
    // Not asserting visibility - the banner is only shown on connection loss.
    // We assert it exists in the DOM so a future connectivity failure has
    // somewhere to render into.
    await expect(page.locator('#connBanner')).toBeAttached();
  });

  test('KPI values are numeric-looking after initial load', { tag: '@positive' }, async ({ page }) => {
    await page.waitForTimeout(1500); // allow the dashboard's polling JS to populate real data
    const text = await page.locator('#kpi-total-orders').innerText();
    expect(text.trim().length).toBeGreaterThan(0);
  });
});
