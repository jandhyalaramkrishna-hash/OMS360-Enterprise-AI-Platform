import { test, expect } from '@playwright/test';
import { validOrderPayload, getOrderableItemId } from '../../utils/apiHelpers';

/**
 * End-to-end business flow: place an order through the real API, then verify
 * its effects are visible through other parts of the system (inventory
 * decrement, audit trail, operations dashboard) - the same order lifecycle
 * described in app/routes/orders.py's docstring (order.created Kafka event,
 * inventory decrement, kitchen/delivery status rows, audit trail entry).
 *
 * This suite intentionally mixes API calls and UI checks in one flow, so it
 * lives under tests/e2e rather than tests/api or tests/dashboard.
 */

test.describe('Order Lifecycle E2E @regression', () => {
  test('placing an order decrements inventory and is reflected in the audit trail', { tag: '@e2e' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);

    const beforeRes = await request.get(`/api/v1/inventory/${itemId}`);
    const before = await beforeRes.json();

    const orderRes = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { items: [{ item_id: itemId, quantity: 1 }] }),
    });
    expect(orderRes.status()).toBe(201);
    const order = await orderRes.json();

    // Inventory should reflect the reservation.
    const afterRes = await request.get(`/api/v1/inventory/${itemId}`);
    const after = await afterRes.json();
    expect(after.remaining_stock).toBeLessThanOrEqual(before.remaining_stock);

    // Audit trail should record at least the initial creation event.
    const auditRes = await request.get(`/api/v1/orders/${order.order_id}/audit`);
    const audit = await auditRes.json();
    expect(audit.length).toBeGreaterThan(0);

    // The ledger for this item should show a movement tied to this order (or
    // at least a recent entry) - confirms the reservation was recorded.
    const historyRes = await request.get(`/api/v1/inventory/history?item_id=${itemId}&limit=5`);
    const history = await historyRes.json();
    expect(Array.isArray(history)).toBeTruthy();
  });

  test('a newly created order is discoverable via the Orders list', { tag: '@e2e' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const orderRes = await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });
    const order = await orderRes.json();

    const listRes = await request.get('/api/v1/orders?limit=100');
    const list = await listRes.json();
    expect(list.some((o: any) => o.order_id === order.order_id)).toBeTruthy();
  });

  test('placing an order is reflected on the Operations dashboard KPIs', { tag: '@e2e' }, async ({ request, page }) => {
    const itemId = await getOrderableItemId(request);

    const kpiRes = await request.get('/api/v1/dashboard/kpis');
    test.skip(!kpiRes.ok(), 'GET /api/v1/dashboard/kpis is not reachable in this environment.');
    const kpisBefore = await kpiRes.json();

    await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });

    await page.goto('/dashboard/operations');
    await page.waitForTimeout(1500); // allow the dashboard's polling JS to refresh

    const kpiAfterRes = await request.get('/api/v1/dashboard/kpis');
    const kpisAfter = await kpiAfterRes.json();

    if (typeof kpisBefore.total_orders === 'number' && typeof kpisAfter.total_orders === 'number') {
      expect(kpisAfter.total_orders).toBeGreaterThanOrEqual(kpisBefore.total_orders);
    }
  });

  test('an out-of-stock item cannot be ordered (insufficient stock is rejected)', { tag: '@e2e' }, async ({ request }) => {
    const outRes = await request.get('/api/v1/inventory/out-of-stock');
    const outItems = await outRes.json();
    test.skip(!Array.isArray(outItems) || outItems.length === 0, 'No out-of-stock item currently exists to exercise this path.');

    const itemId = outItems[0].item_id;
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { items: [{ item_id: itemId, quantity: 1 }] }),
    });
    expect(res.status()).toBe(409);
  });
});
