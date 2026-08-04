import { test, expect } from '@playwright/test';
import { getOrderableItemId } from '../../utils/apiHelpers';

/**
 * app/routes/inventory.py
 *   GET  /api/v1/inventory                 list all
 *   GET  /api/v1/inventory/low-stock
 *   GET  /api/v1/inventory/out-of-stock
 *   GET  /api/v1/inventory/alerts
 *   GET  /api/v1/inventory/history
 *   GET  /api/v1/inventory/{item_id}
 *   POST /api/v1/inventory/restock         RestockRequest { quantity: gt=0, reason? }
 *   PUT  /api/v1/inventory/{item_id}       InventoryUpdateRequest (all fields optional)
 *   POST /api/v1/inventory                 InventoryCreateRequest { item_name, price>0, total_stock>=0, status? }
 *
 * VALID_INVENTORY_STATUSES = ACTIVE | LOW_STOCK | OUT_OF_STOCK | INACTIVE (app/schemas.py)
 *
 * Tests that mutate state create their own item via POST /api/v1/inventory
 * first, rather than mutating seeded rows, so this suite is safe to re-run
 * against a persistent dev database.
 */

async function createTestItem(request: any, overrides: Record<string, any> = {}) {
  const payload = {
    item_name: `PW Test Item ${Date.now()}`,
    price: 99,
    total_stock: 50,
    ...overrides,
  };
  const res = await request.post('/api/v1/inventory', { data: payload });
  return res;
}

test.describe('Inventory API - Positive @regression', () => {
  test('GET /api/v1/inventory lists items', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory');
    expect(res.status()).toBe(200);
    const list = await res.json();
    expect(Array.isArray(list)).toBeTruthy();
  });

  test('GET /api/v1/inventory/low-stock returns 200', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory/low-stock');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBeTruthy();
  });

  test('GET /api/v1/inventory/out-of-stock returns 200', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory/out-of-stock');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBeTruthy();
  });

  test('GET /api/v1/inventory/alerts returns 200', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory/alerts?limit=10');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBeTruthy();
  });

  test('GET /api/v1/inventory/history returns 200', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory/history?limit=10');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBeTruthy();
  });

  test('GET /api/v1/inventory/{item_id} returns a real item', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.get(`/api/v1/inventory/${itemId}`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.item_id).toBe(itemId);
  });

  test('POST /api/v1/inventory creates a new item', { tag: '@positive' }, async ({ request }) => {
    const res = await createTestItem(request);
    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body).toHaveProperty('item_id');
    expect(body.total_stock).toBe(50);
  });

  test('PUT /api/v1/inventory/{item_id} updates price/status/name', { tag: '@positive' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.put(`/api/v1/inventory/${created.item_id}`, {
      data: { price: 149, status: 'ACTIVE', item_name: 'Updated Name' },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.price).toBe(149);
    expect(body.item_name).toBe('Updated Name');
  });

  test('POST /api/v1/inventory/restock increases stock', { tag: '@positive' }, async ({ request }) => {
    const created = await (await createTestItem(request, { total_stock: 10 })).json();
    const before = created.remaining_stock;

    const res = await request.post(`/api/v1/inventory/restock?item_id=${created.item_id}`, {
      data: { quantity: 25, reason: 'Playwright automation restock' },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.remaining_stock).toBe(before + 25);
  });

  test('history for a specific item_id filters correctly', { tag: '@positive' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.get(`/api/v1/inventory/history?item_id=${created.item_id}`);
    expect(res.status()).toBe(200);
    const ledger = await res.json();
    expect(ledger.every((row: any) => row.item_id === created.item_id)).toBeTruthy();
  });
});

test.describe('Inventory API - Negative @regression', () => {
  test('GET /api/v1/inventory/{item_id} returns 404 for unknown item', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get('/api/v1/inventory/ITEM-DOES-NOT-EXIST-XYZ');
    expect(res.status()).toBe(404);
  });

  test('PUT with an invalid status value is rejected', { tag: '@negative' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.put(`/api/v1/inventory/${created.item_id}`, {
      data: { status: 'NOT_A_REAL_STATUS' },
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/inventory without item_name is rejected', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post('/api/v1/inventory', {
      data: { price: 10, total_stock: 5 },
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/inventory with price <= 0 is rejected', { tag: '@negative' }, async ({ request }) => {
    const res = await createTestItem(request, { price: 0 });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/inventory/restock with quantity <= 0 is rejected', { tag: '@negative' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.post(`/api/v1/inventory/restock?item_id=${created.item_id}`, {
      data: { quantity: 0 },
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/inventory/restock for an unknown item_id fails', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post('/api/v1/inventory/restock?item_id=ITEM-DOES-NOT-EXIST-XYZ', {
      data: { quantity: 10 },
    });
    expect(res.ok()).toBeFalsy();
  });
});

test.describe('Inventory API - Boundary @regression', () => {
  test('total_stock = 0 is accepted (ge=0 boundary)', { tag: '@boundary' }, async ({ request }) => {
    const res = await createTestItem(request, { total_stock: 0 });
    expect(res.status()).toBe(201);
  });

  test('total_stock = -1 is rejected (below ge=0 boundary)', { tag: '@boundary' }, async ({ request }) => {
    const res = await createTestItem(request, { total_stock: -1 });
    expect(res.status()).toBe(422);
  });

  test('price at a small positive boundary (0.01) is accepted', { tag: '@boundary' }, async ({ request }) => {
    const res = await createTestItem(request, { price: 0.01 });
    expect(res.status()).toBe(201);
  });

  test('restock quantity = 1 (minimum positive) is accepted', { tag: '@boundary' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.post(`/api/v1/inventory/restock?item_id=${created.item_id}`, {
      data: { quantity: 1 },
    });
    expect(res.status()).toBe(200);
  });

  test('PUT stock = 0 (ge=0 boundary) is accepted as an admin correction', { tag: '@boundary' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.put(`/api/v1/inventory/${created.item_id}`, { data: { stock: 0 } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.remaining_stock).toBe(0);
  });

  test('PUT stock = -1 (below ge=0 boundary) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const created = await (await createTestItem(request)).json();
    const res = await request.put(`/api/v1/inventory/${created.item_id}`, { data: { stock: -1 } });
    expect(res.status()).toBe(422);
  });
});
