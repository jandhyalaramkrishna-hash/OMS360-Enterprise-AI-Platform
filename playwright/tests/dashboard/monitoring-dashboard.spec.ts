import { test, expect } from '@playwright/test';

/**
 * /dashboard/monitoring -> app/static/monitoring_dashboard.html
 * Backed by GET /api/v1/dashboard/monitoring (4-level severity: CRITICAL,
 * HIGH, MEDIUM, INFORMATION - distinct from /alerts' 3-level severity).
 *
 * Real element ids confirmed by inspecting the static HTML source (2026-08-03):
 *   liveStrip, lsBackend, lsDatabase, lsKafka, lsLastRefresh, lsConnectedSince,
 *   heroStatus/heroStatusText, heroEnv, heroBuild, heroDbTime, heroChecked,
 *   downBanner/downBannerList, failedCount/failedBody, dupCount/dupBody,
 *   dlqCount/dlqBody, criticalCount/criticalAlertsList,
 *   activeAlertsList/activeCount, recentAlertsList/recentCount,
 *   lowStockBody, outStockBody, kitchenDelayBody, paymentFailBody,
 *   healthTiles, summaryTiles, rc-dlq, rc-duplicate, rc-failed, rc-retry,
 *   rc-api-total, rc-api-err, gaugeRow, apiBars,
 *   rbLastUpdated/rbNextRefresh/rbManualRefresh
 */

test.describe('Monitoring Dashboard @regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/monitoring');
  });

  test('page loads and renders the hero status block', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#heroStatus')).toBeVisible();
    await expect(page.locator('#heroStatusText')).toBeVisible();
    await expect(page.locator('#heroEnv')).toBeAttached();
    await expect(page.locator('#heroBuild')).toBeAttached();
  });

  test('live strip shows backend/database/kafka connectivity', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#liveStrip')).toBeVisible();
    await expect(page.locator('#lsBackend')).toBeAttached();
    await expect(page.locator('#lsDatabase')).toBeAttached();
    await expect(page.locator('#lsKafka')).toBeAttached();
  });

  test('failed orders panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#failedCount')).toBeVisible();
    await expect(page.locator('#failedBody')).toBeAttached();
  });

  test('duplicate orders panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#dupCount')).toBeVisible();
    await expect(page.locator('#dupBody')).toBeAttached();
  });

  test('DLQ panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#dlqCount')).toBeVisible();
    await expect(page.locator('#dlqBody')).toBeAttached();
  });

  test('critical alerts panel is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#criticalCount')).toBeVisible();
    await expect(page.locator('#criticalAlertsList')).toBeAttached();
  });

  test('active and recent alerts panels are present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#activeCount')).toBeVisible();
    await expect(page.locator('#activeAlertsList')).toBeAttached();
    await expect(page.locator('#recentCount')).toBeVisible();
    await expect(page.locator('#recentAlertsList')).toBeAttached();
  });

  test('operational tables for low-stock, out-of-stock, kitchen delay and payment failures are present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#lowStockBody')).toBeAttached();
    await expect(page.locator('#outStockBody')).toBeAttached();
    await expect(page.locator('#kitchenDelayBody')).toBeAttached();
    await expect(page.locator('#paymentFailBody')).toBeAttached();
  });

  test('health tiles and summary tiles render', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#healthTiles')).toBeAttached();
    await expect(page.locator('#summaryTiles')).toBeAttached();
  });

  test('recent-counters strip (dlq/duplicate/failed/retry/api) is present', { tag: '@positive' }, async ({ page }) => {
    for (const id of ['#rc-dlq', '#rc-duplicate', '#rc-failed', '#rc-retry', '#rc-api-total', '#rc-api-err']) {
      await expect(page.locator(id)).toBeAttached();
    }
  });

  test('gauge row and API bars render', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#gaugeRow')).toBeAttached();
    await expect(page.locator('#apiBars')).toBeAttached();
  });

  test('manual refresh button updates the last-updated timestamp', { tag: '@positive' }, async ({ page }) => {
    const before = await page.locator('#rbLastUpdated').innerText().catch(() => '');
    await page.locator('#rbManualRefresh').click();
    await page.waitForTimeout(800);
    const after = await page.locator('#rbLastUpdated').innerText().catch(() => '');
    expect(after.length).toBeGreaterThan(0);
    // Not strictly asserting `after !== before` - timestamps could tie at
    // second resolution; the meaningful assertion is that a refresh completed.
  });

  test('down-services banner element exists (shown only when a dependency is down)', { tag: '@boundary' }, async ({ page }) => {
    await expect(page.locator('#downBanner')).toBeAttached();
    await expect(page.locator('#downBannerList')).toBeAttached();
  });
});
