import { APIRequestContext } from '@playwright/test';

/**
 * Grounded in app/schemas.py (as of the 2026-08-03 QA automation pass):
 *   - mobile must match ^[6-9]\d{9}$
 *   - pincode must match ^\d{6}$
 *   - item_id must reference a real inventory row or POST /api/v1/orders
 *     returns 400 (UnknownItemError)
 */

/** A valid, freshly-unique 10-digit mobile number (6-9 first digit). */
export function uniqueMobile(): string {
  const tail = Date.now().toString().slice(-9).padStart(9, '0');
  return '9' + tail;
}

/** A valid Idempotency-Key value, unique per call. */
export function uniqueIdempotencyKey(prefix = 'pw'): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

export interface OrderItemInput {
  item_id: string;
  quantity: number;
}

/** Builds a schema-valid OrderCreatePayload body (app/schemas.py::OrderCreatePayload). */
export function validOrderPayload(itemId: string, overrides: Record<string, any> = {}) {
  return {
    customer_name: 'Playwright QA Bot',
    mobile: uniqueMobile(),
    payment_method: 'UPI',
    items: [{ item_id: itemId, quantity: 1 }],
    delivery_address: {
      door_no: '12/B',
      street: 'M G Road',
      city: 'Bengaluru',
      state: 'Karnataka',
      pincode: '560001',
    },
    ...overrides,
  };
}

/**
 * Resolves a real, currently orderable item_id from GET /api/v1/inventory
 * instead of hardcoding one, so tests stay valid regardless of which seed
 * script (database/demo_seed.sql vs enterprise_demo_seed.sql) populated the
 * database. Falls back to the demo_seed.sql convention ("ITEM-BURGER") only
 * if the inventory list can't be read.
 */
export async function getOrderableItemId(request: APIRequestContext): Promise<string> {
  const res = await request.get('/api/v1/inventory');
  if (res.ok()) {
    const list = await res.json();
    if (Array.isArray(list) && list.length > 0) {
      const active = list.find(
        (i: any) => i.status === 'ACTIVE' && Number(i.remaining_stock) > 0
      );
      if (active) return active.item_id;
      return list[0].item_id;
    }
  }
  return 'ITEM-BURGER';
}

/** Resolves the first intent key from GET /api/v1/ai/copilot/catalog, without hardcoding one. */
export async function getFirstIntentKey(request: APIRequestContext): Promise<string | null> {
  const res = await request.get('/api/v1/ai/copilot/catalog');
  if (!res.ok()) return null;
  const body = await res.json();
  const intents = body?.intents;
  if (Array.isArray(intents) && intents.length > 0) return intents[0].key;
  return null;
}

/** Resolves the first learning topic key from GET /api/v1/ai/copilot/learning/topics. */
export async function getFirstLearningTopic(request: APIRequestContext): Promise<string | null> {
  const res = await request.get('/api/v1/ai/copilot/learning/topics');
  if (!res.ok()) return null;
  const body = await res.json();
  const topics = body?.topics;
  if (Array.isArray(topics) && topics.length > 0) return topics[0].topic;
  return null;
}
