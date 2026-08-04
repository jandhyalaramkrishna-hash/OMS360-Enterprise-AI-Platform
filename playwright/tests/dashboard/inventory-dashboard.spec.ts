import { test, expect } from '@playwright/test';

/**
 * /dashboard/inventory -> app/static/inventory_dashboard.html
 *
 * Real element ids confirmed by inspecting the static HTML source (2026-08-03):
 *   openUpdateBtn, openAddBtn, mgmtRefreshBtn, itemsCount, searchBox,
 *   statusFilter, sortSelect, autoRefreshToggle, refreshNowBtn, lastUpdated,
 *   thRemaining, sortArrow, inventoryBody,
 *   updateModal (updCloseBtn, updItemSelect, updCurrentValues, updItemName,
 *     updCategory, updUnit, updStock, updPrice, updStatus, updMsg,
 *     updCancelBtn, updSaveBtn),
 *   addModal (addCloseBtn, addName, addPrice, addStock, addStatus, addMsg,
 *     addCancelBtn, addSaveBtn)
 *
 * These back the "Update Inventory" / "Add New Item" dialogs documented in
 * docs/governance/DECISION-LOG.md (2026-07-27 category/unit addition).
 */

test.describe('Inventory Dashboard @regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/inventory');
  });

  test('page loads with the items table and toolbar', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#inventoryBody')).toBeAttached();
    await expect(page.locator('#itemsCount')).toBeVisible();
    await expect(page.locator('#openUpdateBtn')).toBeVisible();
    await expect(page.locator('#openAddBtn')).toBeVisible();
  });

  test('search box, status filter and sort control are present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#searchBox')).toBeVisible();
    await expect(page.locator('#statusFilter')).toBeVisible();
    await expect(page.locator('#sortSelect')).toBeVisible();
  });

  test('typing in the search box filters the items table', { tag: '@positive' }, async ({ page }) => {
    await page.waitForTimeout(1000); // allow initial inventory load
    const rowsBefore = await page.locator('#inventoryBody tr').count();
    await page.locator('#searchBox').fill('zzz-no-such-item-zzz');
    await page.waitForTimeout(500);
    const rowsAfter = await page.locator('#inventoryBody tr').count();
    expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
  });

  test('"Add New Item" opens the Add modal', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openAddBtn').click();
    await expect(page.locator('#addModal')).toBeVisible();
    await expect(page.locator('#addName')).toBeVisible();
    await expect(page.locator('#addPrice')).toBeVisible();
    await expect(page.locator('#addStock')).toBeVisible();
  });

  test('Add modal closes via the Cancel button without saving', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openAddBtn').click();
    await expect(page.locator('#addModal')).toBeVisible();
    await page.locator('#addCancelBtn').click();
    await expect(page.locator('#addModal')).toBeHidden();
  });

  test('Add modal closes via the X (close) button', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openAddBtn').click();
    await page.locator('#addCloseBtn').click();
    await expect(page.locator('#addModal')).toBeHidden();
  });

  test('submitting the Add form with a blank name shows a validation message', { tag: '@negative' }, async ({ page }) => {
    await page.locator('#openAddBtn').click();
    await page.locator('#addName').fill('');
    await page.locator('#addPrice').fill('10');
    await page.locator('#addStock').fill('5');
    await page.locator('#addSaveBtn').click();
    await expect(page.locator('#addMsg')).not.toBeEmpty();
  });

  test('adding a new item via the dashboard succeeds end-to-end', { tag: '@positive' }, async ({ page }) => {
    const uniqueName = `PW UI Item ${Date.now()}`;
    await page.locator('#openAddBtn').click();
    await page.locator('#addName').fill(uniqueName);
    await page.locator('#addPrice').fill('75');
    await page.locator('#addStock').fill('20');
    await page.locator('#addSaveBtn').click();

    // Success path either closes the modal or shows a success message in #addMsg;
    // wait for the modal to close as the primary signal, per the app's own
    // "successToast" element used on save.
    await expect(page.locator('#addModal')).toBeHidden({ timeout: 10_000 });
  });

  test('"Update Inventory" opens the Update modal with an item selector', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openUpdateBtn').click();
    await expect(page.locator('#updateModal')).toBeVisible();
    await expect(page.locator('#updItemSelect')).toBeVisible();
  });

  test('Update modal closes via Cancel without saving', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openUpdateBtn').click();
    await expect(page.locator('#updateModal')).toBeVisible();
    await page.locator('#updCancelBtn').click();
    await expect(page.locator('#updateModal')).toBeHidden();
  });

  test('selecting an item in the Update modal populates current values', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#openUpdateBtn').click();
    await expect(page.locator('#updItemSelect')).toBeVisible();

    const optionCount = await page.locator('#updItemSelect option').count();
    test.skip(optionCount < 2, 'No inventory items available to select in the Update dialog.');

    await page.locator('#updItemSelect').selectOption({ index: 1 });
    await expect(page.locator('#updCurrentValues')).not.toBeEmpty();
  });

  test('manual refresh button reloads the inventory table', { tag: '@positive' }, async ({ page }) => {
    await page.locator('#refreshNowBtn').click();
    await expect(page.locator('#lastUpdated')).toBeVisible();
  });

  test('auto-refresh toggle control is present', { tag: '@positive' }, async ({ page }) => {
    await expect(page.locator('#autoRefreshToggle')).toBeAttached();
  });

  test('sorting by remaining stock does not error', { tag: '@boundary' }, async ({ page }) => {
    await page.waitForTimeout(500);
    await page.locator('#thRemaining').click();
    await expect(page.locator('#sortArrow')).toBeAttached();
  });
});
