import { test, expect } from '@playwright/test';
import {
  validOrderPayload,
  getOrderableItemId,
  uniqueIdempotencyKey,
} from '../../utils/apiHelpers';

/**
 * app/routes/orders.py
 *   POST   /api/v1/orders                 create_order (Idempotency-Key aware)
 *   GET    /api/v1/orders                 list_orders
 *   GET    /api/v1/orders/{order_id}      get_order
 *   GET    /api/v1/orders/{order_id}/audit get_order_audit_trail
 *
 * Validation source: app/schemas.py::OrderCreatePayload / AddressPayload
 *   - mobile   ^[6-9]\d{9}$   (exactly 10 digits, first digit 6-9)
 *   - pincode  ^\d{6}$        (exactly 6 digits)
 *   - items    min_length=1, each quantity gt=0
 *   - customer_name / door_no / street / city / state: min_length=1
 */

test.describe('Order Management API - Positive @regression', () => {
  test('POST /api/v1/orders creates an order with a valid payload', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });

    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body).toHaveProperty('order_id');
    expect(body).toHaveProperty('transaction_id');
    expect(body.order_status).toBeTruthy();
    expect(body.items.length).toBeGreaterThan(0);
  });

  test('GET /api/v1/orders lists recently created orders', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const createRes = await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });
    const created = await createRes.json();

    const listRes = await request.get('/api/v1/orders?limit=50');
    expect(listRes.status()).toBe(200);
    const list = await listRes.json();
    expect(Array.isArray(list)).toBeTruthy();
    expect(list.some((o: any) => o.order_id === created.order_id)).toBeTruthy();
  });

  test('GET /api/v1/orders/{order_id} returns the created order', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const createRes = await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });
    const created = await createRes.json();

    const getRes = await request.get(`/api/v1/orders/${created.order_id}`);
    expect(getRes.status()).toBe(200);
    const body = await getRes.json();
    expect(body.order_id).toBe(created.order_id);
  });

  test('GET /api/v1/orders/{order_id}/audit returns a non-empty audit trail', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const createRes = await request.post('/api/v1/orders', { data: validOrderPayload(itemId) });
    const created = await createRes.json();

    const auditRes = await request.get(`/api/v1/orders/${created.order_id}/audit`);
    expect(auditRes.status()).toBe(200);
    const events = await auditRes.json();
    expect(Array.isArray(events)).toBeTruthy();
    expect(events.length).toBeGreaterThan(0);
    expect(events[0]).toHaveProperty('event_type');
  });

  test('repeating the same Idempotency-Key returns 409, not a second order', { tag: '@positive' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const payload = validOrderPayload(itemId);
    const key = uniqueIdempotencyKey();

    const first = await request.post('/api/v1/orders', {
      data: payload,
      headers: { 'Idempotency-Key': key },
    });
    expect(first.status()).toBe(201);

    const second = await request.post('/api/v1/orders', {
      data: payload,
      headers: { 'Idempotency-Key': key },
    });
    expect(second.status()).toBe(409);
  });
});

test.describe('Order Management API - Negative @regression', () => {
  test('POST /api/v1/orders rejects an invalid mobile number', { tag: '@negative' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { mobile: '12345' }),
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/orders rejects a mobile not starting with 6-9', { tag: '@negative' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { mobile: '5123456789' }),
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/orders rejects an invalid pincode', { tag: '@negative' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, {
        delivery_address: {
          door_no: '1', street: 'Test St', city: 'Bengaluru', state: 'Karnataka', pincode: '12345',
        },
      }),
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/orders rejects an empty items array', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload('IGNORED', { items: [] }),
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/orders rejects a blank customer_name', { tag: '@negative' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { customer_name: '' }),
    });
    expect(res.status()).toBe(422);
  });

  test('POST /api/v1/orders rejects an unknown item_id with 400', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload('ITEM-DOES-NOT-EXIST-XYZ'),
    });
    expect(res.status()).toBe(400);
  });

  test('POST /api/v1/orders rejects a missing required field (mobile)', { tag: '@negative' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const payload: any = validOrderPayload(itemId);
    delete payload.mobile;
    const res = await request.post('/api/v1/orders', { data: payload });
    expect(res.status()).toBe(422);
  });

  test('GET /api/v1/orders/{order_id} returns 404 for a non-existent order', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get('/api/v1/orders/ORD-DOES-NOT-EXIST');
    expect(res.status()).toBe(404);
  });

  test('GET /api/v1/orders/{order_id}/audit returns 404 for a non-existent order', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get('/api/v1/orders/ORD-DOES-NOT-EXIST/audit');
    expect(res.status()).toBe(404);
  });
});

test.describe('Order Management API - Boundary @regression', () => {
  test('quantity = 1 (minimum positive) is accepted', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { items: [{ item_id: itemId, quantity: 1 }] }),
    });
    expect(res.status()).toBe(201);
  });

  test('quantity = 0 is rejected (gt=0 boundary)', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { items: [{ item_id: itemId, quantity: 0 }] }),
    });
    expect(res.status()).toBe(422);
  });

  test('quantity = -1 (negative) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { items: [{ item_id: itemId, quantity: -1 }] }),
    });
    expect(res.status()).toBe(422);
  });

  test('mobile with 9 digits (below the 10-digit boundary) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { mobile: '987654321' }),
    });
    expect(res.status()).toBe(422);
  });

  test('mobile with 11 digits (above the 10-digit boundary) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, { mobile: '98765432100' }),
    });
    expect(res.status()).toBe(422);
  });

  test('pincode with 5 digits (below the 6-digit boundary) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, {
        delivery_address: { door_no: '1', street: 'St', city: 'Bengaluru', state: 'KA', pincode: '56001' },
      }),
    });
    expect(res.status()).toBe(422);
  });

  test('pincode with 7 digits (above the 6-digit boundary) is rejected', { tag: '@boundary' }, async ({ request }) => {
    const itemId = await getOrderableItemId(request);
    const res = await request.post('/api/v1/orders', {
      data: validOrderPayload(itemId, {
        delivery_address: { door_no: '1', street: 'St', city: 'Bengaluru', state: 'KA', pincode: '5600011' },
      }),
    });
    expect(res.status()).toBe(422);
  });

  test('GET /api/v1/orders respects the limit parameter boundary (limit=1)', { tag: '@boundary' }, async ({ request }) => {
    const res = await request.get('/api/v1/orders?limit=1');
    expect(res.status()).toBe(200);
    const list = await res.json();
    expect(list.length).toBeLessThanOrEqual(1);
  });
});
